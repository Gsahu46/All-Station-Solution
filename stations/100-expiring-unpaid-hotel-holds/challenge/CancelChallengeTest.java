package com.ghoomo.holds;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: DELETE /holds/{id}: the guest changes their mind and the room is free at once. 204 every time, but
 * the room is given back only once, even when the app sends the DELETE five times at the same moment.
 */
class CancelChallengeTest extends ApiTest {

    @Test
    void aCancelledHoldFreesItsRoomOnce() throws Exception {
        hold("changes-mind1", 1, "2026-12-28", "asha@example.com").andExpect(status().isCreated());
        hold("stays-booked1", 1, "2026-12-28", "ravi@example.com").andExpect(status().isCreated());
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> answers = new ArrayList<>();
        try (var taps = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 5; i++) {
                answers.add(taps.submit(() -> {
                    start.await();
                    return mvc.perform(delete("/holds/1")).andReturn().getResponse().getStatus();
                }));
            }
            start.countDown();
        }
        assertThat(answers).extracting(Future::resultNow).containsOnly(204);
        assertThat(held(1, "2026-12-28")).isEqualTo(1);   // Ravi's
        mvc.perform(get("/holds/1")).andExpect(jsonPath("$.status").value("CANCELLED"));
        mvc.perform(delete("/holds/99")).andExpect(status().isNotFound());
    }
}
