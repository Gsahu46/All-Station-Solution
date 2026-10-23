package com.tiffino.orders;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.awaitility.Awaitility.await;

/**
 * The real server on a real port, read the way a browser's EventSource reads it: line by line as it arrives.
 * Streams time out after 10 s here (5 minutes in production; StreamTimeoutTest uses 1 s) and two events are kept per
 * order (50), so old Last-Event-IDs are quick to reach. The heartbeat is called by the tests, not by the clock (every 15 s).
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {"tiffino.sse.timeout=10s", "tiffino.sse.history=2", "tiffino.sse.heartbeat=1h"})
abstract class ApiTest {

    @LocalServerPort
    int port;
    @Autowired
    OrderStreams streams;

    static final HttpClient HTTP = HttpClient.newHttpClient();

    record Sse(String id, String event, String data) {
    }

    /** One open stream: its status code, the events received so far, and whether the server has ended it. */
    static final class Stream implements AutoCloseable {
        final int status;
        final List<Sse> events = new CopyOnWriteArrayList<>();
        final List<String> lines = new CopyOnWriteArrayList<>();
        volatile boolean ended;
        private final InputStream body;

        Stream(HttpResponse<InputStream> response) {
            status = response.statusCode();
            body = response.body();
            Thread.ofVirtual().start(this::read);
        }

        private void read() {
            try (BufferedReader in = new BufferedReader(new InputStreamReader(body, StandardCharsets.UTF_8))) {
                String id = null, event = null;
                List<String> data = new ArrayList<>();
                for (String line; (line = in.readLine()) != null; ) {
                    lines.add(line);
                    if (line.isEmpty()) {
                        if (!data.isEmpty()) {
                            events.add(new Sse(id, event, String.join("\n", data)));
                        }
                        id = null;
                        event = null;
                        data.clear();
                    } else if (line.startsWith("id:")) {
                        id = line.substring(3);
                    } else if (line.startsWith("event:")) {
                        event = line.substring(6);
                    } else if (line.startsWith("data:")) {
                        data.add(line.substring(5));
                    }
                }
            } catch (java.io.IOException closedByUs) {
                // close() below
            } finally {
                ended = true;
            }
        }

        List<Sse> awaitEvents(int count) {
            await().atMost(Duration.ofSeconds(5)).until(() -> events.size() >= count);
            return List.copyOf(events);
        }

        /** The client goes away: closes its side of the connection without the server knowing yet. */
        @Override
        public void close() throws Exception {
            body.close();
        }
    }

    Stream open(String user, long orderId, Long lastEventId) throws Exception {
        HttpRequest.Builder request = HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/orders/" + orderId + "/events"))
                .header("Accept", "text/event-stream").header("Authorization", basic(user));
        if (lastEventId != null) {
            request.header("Last-Event-ID", lastEventId.toString());
        }
        return new Stream(HTTP.send(request.build(), HttpResponse.BodyHandlers.ofInputStream()));
    }

    int advance(long orderId, String status) throws Exception {
        return HTTP.send(HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/orders/" + orderId + "/status"))
                .header("Authorization", basic("kitchen")).header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString("{\"status\":\"" + status + "\"}")).build(), HttpResponse.BodyHandlers.discarding()).statusCode();
    }

    static String basic(String user) {
        return "Basic " + Base64.getEncoder().encodeToString((user + ":" + user + "-demo-pass").getBytes());
    }
}
