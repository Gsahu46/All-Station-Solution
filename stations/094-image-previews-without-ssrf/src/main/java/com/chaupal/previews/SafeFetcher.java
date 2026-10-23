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

    static final class Blocked extends UnknownHostException {
        Blocked(String host) {
            super(host + " resolves to an address that is not allowed");
        }
    }

    private final CloseableHttpClient http;

    SafeFetcher(AddressPolicy policy, NameLookup lookup) {
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
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
        if (!(scheme.equals("http") || scheme.equals("https")) || uri.getHost() == null || uri.getRawUserInfo() != null) {
            throw problem(HttpStatus.BAD_REQUEST, "Only http and https links to a host can be previewed");
        }
        HttpGet get = new HttpGet(uri);
        get.addHeader("Accept", "text/html");
        HttpClientContext context = HttpClientContext.create();
        try {
            return http.execute(get, context, response -> {
                if (response.getCode() != 200) {
                    throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "The page answered " + response.getCode());
                }
                ContentType type = ContentType.parseLenient(response.getEntity().getContentType());
                if (type == null || !type.getMimeType().equalsIgnoreCase("text/html")) {
                    throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "The link is not a web page");
                }
                try (InputStream in = response.getEntity().getContent()) {
                    byte[] head = in.readNBytes(MAX_BYTES);   // a preview needs the head of a page, never the whole of a huge one
                    if (in.read() != -1) {
                        get.cancel();   // more is coming: drop the connection rather than read (or wait for) the rest
                    }
                    var redirects = context.getRedirectLocations().getAll();
                    URI finalUri = redirects.isEmpty() ? uri : redirects.getLast();   // relative links resolve against the page we ended on
                    return new Page(finalUri, new String(head, type.getCharset() == null ? StandardCharsets.UTF_8 : type.getCharset()));
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
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "The page redirects to a link that cannot be previewed");   // file:, no host...
            }
            throw problem(HttpStatus.BAD_GATEWAY, "The page could not be fetched");
        }
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
