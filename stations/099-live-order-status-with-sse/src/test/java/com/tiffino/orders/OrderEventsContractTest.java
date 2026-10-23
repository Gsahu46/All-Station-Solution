package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

class OrderEventsContractTest extends ApiTest {

    @Test
    void aWatcherGetsTheCurrentStatusThenEachChange() throws Exception {
        try (Stream riya = open("riya", 1003, null)) {
            assertThat(riya.status).isEqualTo(200);
            var first = riya.awaitEvents(1).getFirst();
            assertThat(first.event()).isEqualTo("snapshot");
            assertThat(first.id()).isEqualTo("1");
            assertThat(first.data()).contains("\"orderId\":1003", "\"status\":\"PLACED\"");
            assertThat(riya.lines).contains("retry:3000");   // how long the browser waits before reconnecting

            assertThat(advance(1003, "ACCEPTED")).isEqualTo(200);
            assertThat(advance(1003, "COOKING")).isEqualTo(200);
            var events = riya.awaitEvents(3);
            assertThat(events).extracting(Sse::event).containsExactly("snapshot", "status", "status");
            assertThat(events).extracting(Sse::id).containsExactly("1", "2", "3");
            assertThat(events.get(2).data()).contains("\"status\":\"COOKING\"");
        }
    }

    @Test
    void theStreamEndsAtDeliveryAndA204TellsTheBrowserToStop() throws Exception {
        try (Stream riya = open("riya", 1005, null)) {
            for (String status : new String[]{"ACCEPTED", "COOKING", "OUT_FOR_DELIVERY", "DELIVERED"}) {
                assertThat(advance(1005, status)).isEqualTo(200);
            }
            await().atMost(Duration.ofSeconds(5)).until(() -> riya.ended);
            assertThat(riya.events).extracting(Sse::id).containsExactly("1", "2", "3", "4", "5");
        }
        try (Stream sawEverything = open("riya", 1005, 5L)) {
            assertThat(sawEverything.status).isEqualTo(204);   // the HTML standard: 204 means "do not reconnect"
        }
        try (Stream missedTheEnd = open("riya", 1005, 3L)) {
            assertThat(missedTheEnd.awaitEvents(2)).extracting(Sse::id).containsExactly("4", "5");
            await().atMost(Duration.ofSeconds(5)).until(() -> missedTheEnd.ended);
        }
    }

    @Test
    void unknownOrdersSomeoneElsesAndBadRequests() throws Exception {
        assertThat(open("kabir", 1001, null).status).isEqualTo(404);   // Riya's order: as if it did not exist
        assertThat(open("riya", 9999, null).status).isEqualTo(404);
        assertThat(open("riya", 1001, null).status).isEqualTo(200);
        var noSignIn = HTTP.send(HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/orders/1001/events")).build(), HttpResponse.BodyHandlers.discarding());
        assertThat(noSignIn.statusCode()).isEqualTo(401);
        assertThat(open("kitchen", 1001, null).status).isEqualTo(403);
        var badLastId = HTTP.send(HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/orders/1001/events"))
                .header("Authorization", basic("riya")).header("Last-Event-ID", "abc").build(), HttpResponse.BodyHandlers.discarding());
        assertThat(badLastId.statusCode()).isEqualTo(400);

        assertThat(advance(1015, "COOKING")).isEqualTo(409);   // skips ACCEPTED
        assertThat(advance(1015, "EATEN")).isEqualTo(400);
        assertThat(advance(9999, "ACCEPTED")).isEqualTo(404);
    }
}
