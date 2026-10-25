package com.basketo.referrals;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Executors;

/**
 * A simulated wallet service. It credits once per Idempotency-Key, as a well-behaved wallet does, answers with the
 * statuses a test plans (then 200), and records every request it received.
 */
final class TestWallet {

    static final TestWallet WALLET = new TestWallet();
    private static final JsonMapper JSON = JsonMapper.builder().build();

    record Request(String key, JsonNode body) {
    }

    final List<Request> requests = new CopyOnWriteArrayList<>();
    final Map<String, JsonNode> credited = new ConcurrentHashMap<>();
    final Queue<Integer> planned = new ConcurrentLinkedQueue<>();
    /** Apply the next credit, then answer only after this long (longer than the app waits). */
    volatile long slowAfterApplyMillis;
    private final HttpServer server;

    private TestWallet() {
        try {
            server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
        server.createContext("/credits", this::handle);
        server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
        server.start();
    }

    String url() {
        return "http://127.0.0.1:" + server.getAddress().getPort();
    }

    void reset() {
        requests.clear();
        credited.clear();
        planned.clear();
        slowAfterApplyMillis = 0;
    }

    /** Paise credited to a customer, each key counted once. */
    long creditedTo(long customerId) {
        return credited.values().stream().filter(b -> b.path("customerId").asLong() == customerId).mapToLong(b -> b.path("amountPaise").asLong()).sum();
    }

    private void handle(HttpExchange x) throws IOException {
        String key = x.getRequestHeaders().getFirst("Idempotency-Key");
        JsonNode body = JSON.readTree(x.getRequestBody().readAllBytes());
        requests.add(new Request(key, body));
        Integer status = planned.poll();
        if (status != null && status != 200) {
            reply(x, status);
            return;
        }
        credited.putIfAbsent(key, body);
        if (slowAfterApplyMillis > 0) {
            long wait = slowAfterApplyMillis;
            slowAfterApplyMillis = 0;
            try {
                Thread.sleep(wait);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        reply(x, 200);
    }

    private static void reply(HttpExchange x, int status) {
        try {
            x.sendResponseHeaders(status, -1);
        } catch (IOException gone) {
            // the app stopped waiting
        }
        x.close();
    }
}
