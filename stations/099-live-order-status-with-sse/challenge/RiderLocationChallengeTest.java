package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: while an order is out for delivery, the rider's phone sends its position:
 * POST /orders/{id}/location {"lat": 12.97, "lng": 77.59} (the kitchen sign-in stands in for the rider). Watchers get
 * an event named "location", numbered like every other event, so a reconnect replays it too. Before or after the
 * ride: 409.
 */
class RiderLocationChallengeTest extends ApiTest {

    int location(long orderId, String json) throws Exception {
        return HTTP.send(HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/orders/" + orderId + "/location"))
                .header("Authorization", basic("kitchen")).header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json)).build(), HttpResponse.BodyHandlers.discarding()).statusCode();
    }

    @Test
    void watchersSeeTheRiderMove() throws Exception {
        assertThat(location(1051, "{\"lat\":12.97,\"lng\":77.59}")).isEqualTo(409);   // not out for delivery yet
        for (String status : new String[]{"ACCEPTED", "COOKING", "OUT_FOR_DELIVERY"}) {
            assertThat(advance(1051, status)).isEqualTo(200);
        }
        try (Stream riya = open("riya", 1051, 4L)) {
            assertThat(location(1051, "{\"lat\":12.9716,\"lng\":77.5946}")).isEqualTo(200);
            var events = riya.awaitEvents(1);
            assertThat(events.getFirst().event()).isEqualTo("location");
            assertThat(events.getFirst().id()).isEqualTo("5");
            assertThat(events.getFirst().data()).contains("\"lat\":12.9716", "\"lng\":77.5946");
        }
        try (Stream later = open("riya", 1051, 4L)) {   // a reconnect replays the location like any event
            assertThat(later.awaitEvents(1).getFirst().event()).isEqualTo("location");
        }
    }

    @Test
    void badPositionsAre400() throws Exception {
        assertThat(location(1053, "{\"lat\":91,\"lng\":77.59}")).isEqualTo(400);
        assertThat(location(1053, "{\"lat\":12.97}")).isEqualTo(400);
        assertThat(location(9999, "{\"lat\":12.97,\"lng\":77.59}")).isEqualTo(404);
    }
}
