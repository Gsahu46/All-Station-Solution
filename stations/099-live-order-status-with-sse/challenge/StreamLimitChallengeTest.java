package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/**
 * Challenge 2: a limit on open streams per customer, tiffino.sse.max-streams-per-customer (a demo rule: 50 by
 * default, 3 in this test). An app stuck in a reconnect loop gets 429 with Retry-After instead of opening hundreds;
 * when one of its streams ends, it may open another.
 */
@org.springframework.test.context.TestPropertySource(properties = "tiffino.sse.max-streams-per-customer=3")
class StreamLimitChallengeTest extends ApiTest {

    @Test
    void theFourthOpenStreamIs429() throws Exception {
        List<Stream> open = new ArrayList<>();
        for (int i = 0; i < 3; i++) {
            open.add(open("kabir", 1062, null));
        }
        open.forEach(s -> s.awaitEvents(1));
        try (Stream fourth = open("kabir", 1064, null)) {
            assertThat(fourth.status).isEqualTo(429);
        }
        try (Stream riya = open("riya", 1061, null)) {
            assertThat(riya.status).isEqualTo(200);   // another customer is not affected
        }
        open.getFirst().close();   // one phone goes away; the next heartbeat notices
        await().atMost(Duration.ofSeconds(5)).until(() -> {
            streams.heartbeat();
            try (Stream again = open("kabir", 1062, null)) {
                return again.status == 200;
            }
        });
        for (Stream s : open) {
            s.close();
        }
    }
}
