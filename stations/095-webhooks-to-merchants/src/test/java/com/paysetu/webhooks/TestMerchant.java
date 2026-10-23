package com.paysetu.webhooks;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Executors;
import java.util.function.IntSupplier;

/** A merchant's server for the tests: records what arrives, answers what the test tells it to. */
final class TestMerchant implements AutoCloseable {

    record Received(String id, String timestamp, String signature, String contentType, String body, Instant at) {
        /** What the merchant runs, at the moment the request arrived. */
        boolean verifiedWith(String secret) {
            return WebhookSignature.verify(secret, id, timestamp, signature, body, at);
        }
    }

    private final HttpServer server;
    private final Clock clock;
    private final List<Received> received = new CopyOnWriteArrayList<>();
    volatile IntSupplier answer = () -> 200;
    volatile long delayMillis;

    TestMerchant(Clock clock) throws IOException {
        this.clock = clock;
        server = HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress(), 0), 0);
        server.createContext("/hooks/paysetu", this::handle);
        server.createContext("/elsewhere", x -> {
            received.add(new Received(null, null, null, null, "at /elsewhere", clock.instant()));
            reply(x, 200);
        });
        server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
        server.start();
    }

    String url() {
        return "http://127.0.0.1:" + server.getAddress().getPort() + "/hooks/paysetu";
    }

    List<Received> received() {
        return List.copyOf(received);
    }

    private void handle(HttpExchange x) throws IOException {
        var h = x.getRequestHeaders();
        received.add(new Received(h.getFirst("webhook-id"), h.getFirst("webhook-timestamp"), h.getFirst("webhook-signature"),
                h.getFirst("Content-Type"), new String(x.getRequestBody().readAllBytes(), StandardCharsets.UTF_8), clock.instant()));
        if (delayMillis > 0) {
            try {
                Thread.sleep(delayMillis);   // a slow merchant, to hit the timeout
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        int status = answer.getAsInt();
        if (status / 100 == 3) {
            x.getResponseHeaders().add("Location", "/elsewhere");
        }
        reply(x, status);
    }

    private static void reply(HttpExchange x, int status) throws IOException {
        x.sendResponseHeaders(status, -1);
        x.close();
    }

    @Override
    public void close() {
        server.stop(0);
    }
}
