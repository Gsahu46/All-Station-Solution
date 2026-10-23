package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/** Streams that end after 1 s, so the server's timeout and the client's reconnect can be watched. */
@TestPropertySource(properties = "tiffino.sse.timeout=1s")
class StreamTimeoutTest extends ApiTest {

    @Test
    void aStreamTimesOutAndTheClientResumesWithoutMissingAnything() throws Exception {
        String lastId;
        try (Stream riya = open("riya", 1011, null)) {
            lastId = riya.awaitEvents(1).getLast().id();
            await().atMost(Duration.ofSeconds(5)).until(() -> riya.ended);   // the server ended it after 1 s
        }
        assertThat(advance(1011, "ACCEPTED")).isEqualTo(200);
        try (Stream again = open("riya", 1011, Long.parseLong(lastId))) {
            assertThat(again.awaitEvents(1)).extracting(Sse::id).containsExactly("2");
        }
    }

    @Test
    void aStreamThatTimedOutIsNoLongerHeld() throws Exception {
        try (Stream riya = open("riya", 1017, null)) {
            riya.awaitEvents(1);
            assertThat(streams.streams()).isPositive();
            // Every stream in this test ends after 1 s, and each one that ends leaves the list.
            await().atMost(Duration.ofSeconds(5)).until(() -> riya.ended && streams.streams() == 0);
        }
    }
}
