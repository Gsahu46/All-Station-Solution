package com.chaupal.previews;

import org.apache.hc.client5.http.DnsResolver;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.config.ConnectionConfig;
import org.apache.hc.client5.http.config.RequestConfig;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManagerBuilder;
import org.apache.hc.client5.http.protocol.HttpClientContext;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.util.Timeout;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Component;
import org.springframework.web.ErrorResponseException;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetAddress;
import java.net.SocketTimeoutException;
import java.net.URI;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/**
 * Fetches a page for a preview, safely. Every name is resolved once, by our resolver, which refuses it if any of its
 * addresses is blocked; the connection then goes to exactly those addresses. So a check cannot be fooled by a name
 * that answers differently the second time (DNS rebinding), and redirects go through the same check.
 */
@Component
class SafeFetcher {

    static final int MAX_BYTES = 512 * 1024;
    static final int MAX_REDIRECTS = 3;

    record Page(URI finalUri, String html) {
    }

    record Fetched(URI finalUri, String mimeType, java.nio.charset.Charset charset, byte[] head) {
    }

    static final class Blocked extends UnknownHostException {
        Blocked(String host) {
            super(host + " resolves to an address that is not allowed");
        }
    }

    private final CloseableHttpClient http;

    private final java.util.List<String> allowedDomains;

    SafeFetcher(AddressPolicy policy, NameLookup lookup, @org.springframework.beans.factory.annotation.Value("${chaupal.previews.allowed-domains:}") java.util.List<String> allowedDomains) {
        this.allowedDomains = allowedDomains.stream().map(d -> d.strip().toLowerCase(Locale.ROOT)).filter(d -> !d.isEmpty()).toList();
        DnsResolver checked = new DnsResolver() {
            @Override
            public InetAddress[] resolve(String host) throws UnknownHostException {
                InetAddress[] all = lookup.lookup(host);
                for (InetAddress a : all) {
                    if (policy.isBlocked(a)) {
                        throw new Blocked(host);   // one bad address is enough: the client could pick it
                    }
                }
                return all;
            }

            @Override
            public String resolveCanonicalHostname(String host) {
                return host;
            }
        };
        this.http = HttpClients.custom()
                .setConnectionManager(PoolingHttpClientConnectionManagerBuilder.create().setDnsResolver(checked)
                        .setDefaultConnectionConfig(ConnectionConfig.custom().setConnectTimeout(Timeout.ofSeconds(2)).setSocketTimeout(Timeout.ofSeconds(3)).build())
                        .build())
                .setDefaultRequestConfig(RequestConfig.custom().setResponseTimeout(Timeout.ofSeconds(3)).setMaxRedirects(MAX_REDIRECTS).build())
                .disableCookieManagement()
                .setUserAgent("ChaupalPreview/1.0")
                .build();
    }

    Page fetch(URI uri) {
        Fetched f = fetch(uri, "text/html", MAX_BYTES, "The link is not a web page");
        return new Page(f.finalUri(), new String(f.head(), f.charset()));
    }

    /** Fetches with every check; accept is a type ("text/html") or a family ("image/"). */
    Fetched fetch(URI uri, String accept, int maxBytes, String wrongType) {
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
        if (!(scheme.equals("http") || scheme.equals("https")) || uri.getHost() == null || uri.getRawUserInfo() != null) {
            throw problem(HttpStatus.BAD_REQUEST, "Only http and https links to a host can be previewed");
        }
        String host = uri.getHost().toLowerCase(Locale.ROOT);
        if (!allowedDomains.isEmpty() && allowedDomains.stream().noneMatch(d -> host.equals(d) || host.endsWith("." + d))) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "This site cannot be previewed");   // "fakenews.example" does not end with ".news.example"
        }
        HttpGet get = new HttpGet(uri);
        get.addHeader("Accept", accept.endsWith("/") ? accept + "*" : accept);
        HttpClientContext context = HttpClientContext.create();
        try {
            return http.execute(get, context, response -> {
                if (response.getCode() != 200) {
                    throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "The page answered " + response.getCode());
                }
                ContentType type = ContentType.parseLenient(response.getEntity().getContentType());
                String mime = type == null ? "" : type.getMimeType().toLowerCase(Locale.ROOT);
                if (accept.endsWith("/") ? !mime.startsWith(accept) : !mime.equals(accept)) {
                    throw problem(HttpStatus.UNPROCESSABLE_CONTENT, wrongType);
                }
                try (InputStream in = response.getEntity().getContent()) {
                    byte[] head = in.readNBytes(maxBytes);
                    if (in.read() != -1) {
                        get.cancel();   // more is coming: drop the connection rather than read (or wait for) the rest
                    }
                    var redirects = context.getRedirectLocations().getAll();
                    return new Fetched(redirects.isEmpty() ? uri : redirects.getLast(), mime,
                            type.getCharset() == null ? StandardCharsets.UTF_8 : type.getCharset(), head);
                }
            });
        } catch (ErrorResponseException e) {
            throw e;
        } catch (Blocked e) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "This address cannot be previewed");
        } catch (UnknownHostException e) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "No such host");
        } catch (SocketTimeoutException e) {   // ConnectTimeoutException is one too
            throw problem(HttpStatus.GATEWAY_TIMEOUT, "The page took too long to answer");
        } catch (IOException e) {
            if (e.getCause() instanceof org.apache.hc.client5.http.RedirectException) {
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Too many redirects");
            }
            if (e.getCause() instanceof org.apache.hc.core5.http.ProtocolException) {
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "The page redirects to a link that cannot be previewed");
            }
            throw problem(HttpStatus.BAD_GATEWAY, "The page could not be fetched");
        }
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
