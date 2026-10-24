package com.taskloom.support;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Executors;

/**
 * A simulated model provider in the shape of Anthropic's Messages API. It does not summarise: it answers what the test
 * says, and records every request exactly as it arrived, so tests can check what left Taskloom.
 */
final class TestModel {

    static final TestModel MODEL = new TestModel();
    private static final JsonMapper JSON = JsonMapper.builder().build();
    final List<JsonNode> requests = new CopyOnWriteArrayList<>();
    final List<Map<String, String>> headers = new CopyOnWriteArrayList<>();
    volatile String reply;
    volatile int status;
    volatile long delayMillis;
    volatile int inputTokens;
    volatile int outputTokens;
    private final HttpServer server;

    private TestModel() {
        try {
            server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
        server.createContext("/v1/messages", this::handle);
        server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
        server.start();
        reset();
    }

    String url() {
        return "http://127.0.0.1:" + server.getAddress().getPort() + "/v1/messages";
    }

    void reset() {
        requests.clear();
        headers.clear();
        reply = "- The customer was charged twice for the Pro plan.\n- A refund of the second charge has been requested.";
        status = 200;
        delayMillis = 0;
        inputTokens = 900;
        outputTokens = 60;
    }

    JsonNode last() {
        return requests.getLast();
    }

    private void handle(HttpExchange x) throws IOException {
        requests.add(JSON.readTree(x.getRequestBody().readAllBytes()));
        headers.add(Map.of("x-api-key", String.valueOf(x.getRequestHeaders().getFirst("x-api-key")),
                "anthropic-version", String.valueOf(x.getRequestHeaders().getFirst("anthropic-version"))));
        try {
            Thread.sleep(delayMillis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        String body = status == 200
                ? JSON.writeValueAsString(Map.of("id", "msg_test", "type", "message", "role", "assistant",
                        "content", List.of(Map.of("type", "text", "text", reply)), "stop_reason", "end_turn",
                        "usage", Map.of("input_tokens", inputTokens, "output_tokens", outputTokens)))
                : "{\"type\":\"error\",\"error\":{\"type\":\"overloaded_error\",\"message\":\"Overloaded\"}}";
        byte[] out = body.getBytes(StandardCharsets.UTF_8);
        x.getResponseHeaders().set("Content-Type", "application/json");
        try {
            x.sendResponseHeaders(status, out.length);
            x.getResponseBody().write(out);
        } catch (IOException gone) {
            // the app stopped waiting
        }
        x.close();
    }
}
