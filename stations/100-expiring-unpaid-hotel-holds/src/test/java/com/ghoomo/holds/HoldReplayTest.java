package com.ghoomo.holds;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The guest's app retries "Hold this room" after a timeout: one hold, one room. */
class HoldReplayTest extends ApiTest {

    @Test
    void theSameRequestTwiceIsOneHold() throws Exception {
        // The one suite: the retry must find the guest's own hold, not "sold out".
        hold("retry-me-0001", 2, "2026-12-27", "asha@example.com").andExpect(status().isCreated()).andExpect(jsonPath("$.id").value(1));
        // The retry: the same request (e-mails are compared lower-cased, with Locale.ROOT).
        hold("retry-me-0001", 2, "2026-12-27", "ASHA@Example.com").andExpect(status().isOk()).andExpect(jsonPath("$.id").value(1));
        assertThat(held(2, "2026-12-27")).isEqualTo(1);
        hold("retry-me-0001", 1, "2026-12-28", "asha@example.com").andExpect(status().isUnprocessableContent());   // the same key for another night
        assertThat(held(1, "2026-12-28")).isZero();
    }

    @Test
    void tenCopiesAtTheSameMomentAreOneHold() throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<String>> answers = new ArrayList<>();
        try (var copies = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 10; i++) {
                answers.add(copies.submit(() -> {
                    start.await();
                    var r = hold("same-moment-01", 1, "2026-12-26", "asha@example.com").andReturn().getResponse();
                    return r.getStatus() + " " + JSON.readTree(r.getContentAsString()).get("id").asLong();
                }));
            }
            start.countDown();
        }
        assertThat(answers).extracting(Future::resultNow).filteredOn(a -> a.startsWith("201")).hasSize(1);
        assertThat(answers).extracting(Future::resultNow).extracting(a -> a.split(" ")[1]).containsOnly("1");
        assertThat(held(1, "2026-12-26")).isEqualTo(1);
    }
}
