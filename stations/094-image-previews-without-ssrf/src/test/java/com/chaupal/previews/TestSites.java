package com.chaupal.previews;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Two small web servers on the same port: a "public" news site on 127.0.0.2 and an "internal" metadata service on
 * 127.0.0.1 that hands out a secret, like a cloud instance's. And a stand-in for DNS that points names at them.
 */
final class TestSites {

    static final String SECRET = "AKIA-DEMO-SECRET-KEY";
    static final int PORT;
    static final AtomicInteger rebindLookups = new AtomicInteger();

    static {
        try {
            HttpServer news = HttpServer.create(new InetSocketAddress(InetAddress.getByName("127.0.0.2"), 0), 0);
            PORT = news.getAddress().getPort();
            HttpServer internal = HttpServer.create(new InetSocketAddress(InetAddress.getByName("127.0.0.1"), PORT), 0);
            internal.createContext("/", x -> send(x, 200, "text/plain", SECRET));
            news.createContext("/", TestSites::news);
            news.setExecutor(java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor());
            internal.start();
            news.start();
        } catch (IOException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    static String url(String host, String path) {
        return "http://" + host + ":" + PORT + path;
    }

    /** DNS for the tests. rebind.example answers the public address, then the internal one, and so on (a 0-second TTL). */
    static InetAddress[] lookup(String host) throws UnknownHostException {
        Map<String, String> names = Map.of("news.example", "127.0.0.2", "metadata.internal", "127.0.0.1");
        if (names.containsKey(host)) {
            return new InetAddress[]{InetAddress.getByName(names.get(host))};
        }
        if (host.equals("rebind.example")) {
            return new InetAddress[]{InetAddress.getByName(rebindLookups.incrementAndGet() % 2 == 1 ? "127.0.0.2" : "127.0.0.1")};
        }
        if (host.equals("mixed.example")) {
            return new InetAddress[]{InetAddress.getByName("127.0.0.2"), InetAddress.getByName("10.0.0.5")};
        }
        if (host.endsWith(".example")) {
            throw new UnknownHostException(host);
        }
        return InetAddress.getAllByName(host);   // IP literals
    }

    private static void news(HttpExchange x) throws IOException {
        String path = x.getRequestURI().getPath();
        switch (path) {
            case "/article" -> send(x, 200, "text/html; charset=utf-8", """
                    <html><head><title>Monsoon reaches Kerala</title>
                    <meta property="og:title" content="Monsoon reaches Kerala early">
                    <meta property="og:description" content="Rain in Kochi &amp; Thiruvananthapuram.">
                    <meta property="og:image" content="/img/cover.jpg"></head><body>...</body></html>""");
            case "/image.png" -> send(x, 200, "image/png", "PNG");
            case "/gone" -> send(x, 404, "text/html", "<title>Not found</title>");
            case "/to-metadata" -> redirect(x, url("127.0.0.1", "/latest/meta-data/iam/security-credentials/"));
            case "/to-article" -> redirect(x, "/article");
            case "/to-file" -> redirect(x, "file:///etc/passwd");
            case "/loop" -> redirect(x, "/loop");
            case "/slow" -> {
                sleep(10_000);
                send(x, 200, "text/html", "<title>late</title>");
            }
            case "/huge" -> {
                x.getResponseHeaders().set("Content-Type", "text/html");
                x.sendResponseHeaders(200, 0);
                try (OutputStream out = x.getResponseBody()) {
                    out.write("<html><head>".getBytes());
                    out.write(" ".repeat(600 * 1024).getBytes());   // past the 512 KB a preview reads
                    out.write("<title>far down</title>".getBytes());
                    out.flush();
                    sleep(10_000);   // and the rest never comes
                } catch (IOException closedByTheReader) {
                    // expected: the reader stopped early
                }
            }
            default -> send(x, 404, "text/plain", "no");
        }
    }

    private static void redirect(HttpExchange x, String location) throws IOException {
        x.getResponseHeaders().set("Location", location);
        x.sendResponseHeaders(302, -1);
        x.close();
    }

    private static void send(HttpExchange x, int status, String type, String body) throws IOException {
        byte[] b = body.getBytes(StandardCharsets.UTF_8);
        x.getResponseHeaders().set("Content-Type", type);
        x.sendResponseHeaders(status, b.length);
        try (OutputStream out = x.getResponseBody()) {
            out.write(b);
        }
    }

    private static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private TestSites() {
    }
}
