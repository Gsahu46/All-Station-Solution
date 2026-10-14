package com.teamdesk.holidays;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * A stand-in for the holiday provider: a real HTTP server on a random port (the JDK's own, no extra library), told
 * per test how to behave. Our app calls it over real HTTP, so timeouts and status codes are real too.
 */
final class StubProvider {

    enum Behaviour { NORMAL, SLOW, FAIL, NOT_FOUND, BAD_KEY, BAD_JSON, HANG_UP }

    static final String HOLIDAYS = """
            {"country":"IN","region":"KA","year":2026,"apiVersion":"3.2",
             "holidays":[{"date":"2026-11-01","name":"Kannada Rajyotsava","type":"STATE","observed":true},
                         {"date":"2026-01-26","name":"Republic Day","type":"NATIONAL","observed":true}]}""";

    private final HttpServer server;
    volatile Behaviour behaviour = Behaviour.NORMAL;
    volatile String lastQuery;
    volatile String lastApiKey;
    final AtomicInteger calls = new AtomicInteger();

    private StubProvider(HttpServer server) {
        this.server = server;
    }

    static StubProvider start() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
            server.setExecutor(Executors.newCachedThreadPool());   // a slow answer must not block the next request
            StubProvider stub = new StubProvider(server);
            server.createContext("/v1/holidays", stub::handle);
            server.start();
            return stub;
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    String baseUrl() {
        return "http://localhost:" + server.getAddress().getPort();
    }

    private void handle(HttpExchange ex) throws IOException {
        calls.incrementAndGet();
        lastQuery = ex.getRequestURI().getQuery();
        lastApiKey = ex.getRequestHeaders().getFirst("X-Api-Key");
        switch (behaviour) {
            case NORMAL -> send(ex, 200, HOLIDAYS);
            case SLOW -> {
                sleep(2_000);
                send(ex, 200, HOLIDAYS);
            }
            case FAIL -> send(ex, 500, "{\"error\":\"db-holidays-02.internal:5432 connection pool exhausted\"}");
            case NOT_FOUND -> send(ex, 404, "{\"error\":\"no data for region\"}");
            case BAD_KEY -> send(ex, 401, "{\"error\":\"api key tdk_live_8f2c expired\"}");
            case BAD_JSON -> send(ex, 200, "<html>Service temporarily unavailable</html>");
            case HANG_UP -> ex.close();   // closes the connection without an answer
        }
    }

    private static void send(HttpExchange ex, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().add("Content-Type", "application/json");
        ex.sendResponseHeaders(status, bytes.length);
        ex.getResponseBody().write(bytes);
        ex.close();
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
