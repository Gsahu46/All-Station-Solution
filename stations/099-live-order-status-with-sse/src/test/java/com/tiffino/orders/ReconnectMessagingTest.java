package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertTimeoutPreemptively;
import static org.awaitility.Awaitility.await;

class ReconnectMessagingTest extends ApiTest {

    @Test
    void reconnectingWithLastEventIdGetsOnlyWhatWasMissed() throws Exception {
        try (Stream before = open("riya", 1007, null)) {
            assertThat(before.awaitEvents(1).getFirst().id()).isEqualTo("1");
        }
        assertThat(advance(1007, "ACCEPTED")).isEqualTo(200);   // while the phone is in a tunnel
        try (Stream after = open("riya", 1007, 1L)) {
            assertThat(advance(1007, "COOKING")).isEqualTo(200);
            var events = after.awaitEvents(2);
            assertThat(events).extracting(Sse::id).containsExactly("2", "3");   // no snapshot, nothing twice
            assertThat(events).extracting(Sse::event).containsOnly("status");
        }
        // Nothing missed: the stream still answers at once (status and headers), then waits for the next event.
        Stream upToDate = assertTimeoutPreemptively(Duration.ofSeconds(2), () -> open("riya", 1007, 3L));
        try (upToDate) {
            assertThat(upToDate.status).isEqualTo(200);
            await().during(Duration.ofMillis(300)).until(upToDate.events::isEmpty);
        }
    }

    @Test
    void aLastEventIdOlderThanTheKeptEventsGetsASnapshotInstead() throws Exception {
        for (String status : new String[]{"ACCEPTED", "COOKING", "OUT_FOR_DELIVERY"}) {
            assertThat(advance(1009, status)).isEqualTo(200);   // events 2, 3, 4; only 3 and 4 are kept here
        }
        try (Stream late = open("riya", 1009, 1L)) {
            var first = late.awaitEvents(1).getFirst();
            assertThat(first.event()).isEqualTo("snapshot");   // event 2 is gone: the current status, not a hole
            assertThat(first.id()).isEqualTo("4");
            assertThat(first.data()).contains("\"status\":\"OUT_FOR_DELIVERY\"");
            await().during(Duration.ofMillis(300)).until(() -> late.events.size() == 1);
        }
    }

    @Test
    void everyWatcherGetsEveryChangeOnceAndInOrder() throws Exception {
        List<Stream> watchers = new ArrayList<>();
        try (var phones = Executors.newVirtualThreadPerTaskExecutor()) {   // at once: 30 sign-ins (BCrypt) one after another are slow
            List<Future<Stream>> opening = new ArrayList<>();
            for (int i = 0; i < 30; i++) {
                opening.add(phones.submit(() -> open("riya", 1013, null)));
            }
            for (Future<Stream> f : opening) {
                watchers.add(f.get());
            }
        }
        watchers.forEach(w -> w.awaitEvents(1));
        for (String status : new String[]{"ACCEPTED", "COOKING", "OUT_FOR_DELIVERY", "DELIVERED"}) {
            assertThat(advance(1013, status)).isEqualTo(200);
        }
        for (Stream w : watchers) {
            assertThat(w.awaitEvents(5)).extracting(Sse::id).containsExactly("1", "2", "3", "4", "5");
            await().atMost(Duration.ofSeconds(5)).until(() -> w.ended);
            w.close();
        }
    }
}
