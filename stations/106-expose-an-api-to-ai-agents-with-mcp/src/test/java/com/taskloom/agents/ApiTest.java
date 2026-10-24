package com.taskloom.agents;

import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.client.transport.HttpClientStreamableHttpTransport;
import io.modelcontextprotocol.spec.McpSchema;
import org.junit.jupiter.api.AfterEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** The whole app on a real port, called by the MCP Java SDK's own client over Streamable HTTP, as an agent would. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
abstract class ApiTest {

    static final JsonMapper JSON = JsonMapper.builder().build();
    static final String READER = "demo-kirana-reader", WRITER = "demo-kirana-writer", STUDIO = "demo-studio-writer", CALENDAR = "demo-kirana-calendar";
    static final String INITIALIZE = "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1\"}}}";

    @LocalServerPort
    int port;
    @Autowired
    MockMvc mvc;
    private final List<McpSyncClient> clients = new ArrayList<>();

    /** An agent connected with this token: initialized and ready. */
    McpSyncClient agent(String token) {
        var transport = HttpClientStreamableHttpTransport.builder("http://localhost:" + port).endpoint("/mcp")
                .requestBuilder(HttpRequest.newBuilder().header("Authorization", "Bearer " + token)).build();
        McpSyncClient client = McpClient.sync(transport).requestTimeout(Duration.ofSeconds(10)).build();
        clients.add(client);
        client.initialize();
        return client;
    }

    @AfterEach
    void disconnect() {
        clients.forEach(McpSyncClient::closeGracefully);
        clients.clear();
    }

    static McpSchema.CallToolResult call(McpSyncClient agent, String tool, Map<String, Object> arguments) {
        return agent.callTool(new McpSchema.CallToolRequest(tool, arguments));
    }

    static String text(McpSchema.CallToolResult result) {
        return ((McpSchema.TextContent) result.content().getFirst()).text();
    }

    /** A successful tool result's JSON. */
    static JsonNode json(McpSchema.CallToolResult result) {
        if (Boolean.TRUE.equals(result.isError())) {
            throw new AssertionError("tool error: " + text(result));
        }
        return JSON.readTree(text(result));
    }

    static List<String> ids(JsonNode tasks) {
        List<String> ids = new ArrayList<>();
        tasks.forEach(t -> ids.add(t.path("id").asString()));
        return ids;
    }

    /** A raw POST to /mcp, for what the SDK client would not send. */
    HttpResponse<String> rawPost(String body, String... headers) throws Exception {
        var request = HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/mcp")).POST(HttpRequest.BodyPublishers.ofString(body))
                .header("Content-Type", "application/json").header("Accept", "application/json, text/event-stream");
        for (int i = 0; i < headers.length; i += 2) {
            request.header(headers[i], headers[i + 1]);
        }
        try (HttpClient http = HttpClient.newHttpClient()) {
            return http.send(request.build(), HttpResponse.BodyHandlers.ofString());
        }
    }
}
