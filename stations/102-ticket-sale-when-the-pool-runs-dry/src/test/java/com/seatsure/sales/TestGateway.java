package com.seatsure.sales;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** A payment gateway for the tests: answers each charge after `delayMillis`, with `status` (201 authorised, 402 declined). */
final class TestGateway {

    static final TestGateway GATEWAY = new TestGateway();
    final List<String> idempotencyKeys = new CopyOnWriteArrayList<>();
    volatile long delayMillis;
    volatile int status = 201;
    private final HttpServer server;

    private TestGateway() {
        try {
            server = HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress(), 0), 0);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
        server.createContext("/charges", this::charge);
        server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
        server.start();
    }

    String url() {
        return "http://127.0.0.1:" + server.getAddress().getPort();
    }

    void reset() {
        idempotencyKeys.clear();
        delayMillis = 0;
        status = 201;
    }

    private void charge(HttpExchange x) throws IOException {
        idempotencyKeys.add(x.getRequestHeaders().getFirst("Idempotency-Key"));
        Matcher order = Pattern.compile("\"orderId\":(\\d+)").matcher(new String(x.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
        try {
            Thread.sleep(delayMillis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        byte[] body = (status == 201 ? "{\"chargeId\":\"ch_" + (order.find() ? order.group(1) : "x") + "\"}" : "{\"error\":\"declined\"}").getBytes(StandardCharsets.UTF_8);
        x.getResponseHeaders().add("Content-Type", "application/json");
        try {
            x.sendResponseHeaders(status, body.length);
            x.getResponseBody().write(body);
        } catch (IOException clientGaveUp) {
            // the app timed out and closed the connection
        }
        x.close();
    }
}
