package com.mapwise.edge;

import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.net.InetAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Base64;

/**
 * The real server on a real port: X-Forwarded-* headers are handled inside Tomcat, which MockMvc does not run.
 * In these tests the load balancer is 127.0.0.1; anything else (127.0.0.2) is a client talking to the app directly.
 * Tomcat waits 1 s (not 20 s) for the next bytes of a request, and uploads are limited to 1 MiB (not 10 MiB).
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {"server.tomcat.remoteip.internal-proxies=127.0.0.1/32", "server.tomcat.connection-timeout=1s", "mapwise.max-upload-bytes=1048576"})
abstract class ApiTest {

    static final String BALANCER = "127.0.0.1";
    static final String DIRECT = "127.0.0.2";
    static final JsonMapper JSON = JsonMapper.builder().build();

    @LocalServerPort
    int port;

    HttpRequest.Builder request(String path) {
        return HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + path));
    }

    /** The request as it reaches the app: from the balancer's address, or from a client's own. */
    HttpResponse<String> send(String from, HttpRequest.Builder request) throws Exception {
        try (HttpClient client = HttpClient.newBuilder().localAddress(InetAddress.getByName(from)).build()) {
            return client.send(request.build(), HttpResponse.BodyHandlers.ofString());
        }
    }

    /** What the load balancer adds: the client's address (appended), https, and the public host name. */
    HttpRequest.Builder viaBalancer(String path, String forwardedFor) {
        return request(path).header("X-Forwarded-For", forwardedFor).header("X-Forwarded-Proto", "https").header("X-Forwarded-Host", "maps.mapwise.example");
    }

    static HttpRequest.Builder as(String user, HttpRequest.Builder request) {
        return request.header("Authorization", "Basic " + Base64.getEncoder().encodeToString((user + ":" + user + "-demo-pass").getBytes()));
    }

    static JsonNode json(HttpResponse<String> response) {
        return JSON.readTree(response.body());
    }
}
