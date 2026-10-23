package com.ghoomo.holds;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class HoldConcurrencyTest extends ApiTest {

    @Test
    void twentyGuestsAtOnceForFiveRoomsGetExactlyFive() throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> answers = new ArrayList<>();
        try (var guests = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 20; i++) {
                int n = i;
                answers.add(guests.submit(() -> {
                    start.await();
                    return hold("guest-key-" + (100 + n), 1, "2026-12-30", "g" + n + "@example.com").andReturn().getResponse().getStatus();
                }));
            }
            start.countDown();
        }
        assertThat(answers).extracting(Future::resultNow).filteredOn(s -> s == 201).hasSize(5);
        assertThat(answers).extracting(Future::resultNow).filteredOn(s -> s == 409).hasSize(15);
        assertThat(held(1, "2026-12-30")).isEqualTo(5);
        assertThat(active(1, "2026-12-30")).isEqualTo(5);
    }

    @Test
    void fourExpiryRunsAtOnceGiveEachRoomBackOnce() throws Exception {
        for (int i = 0; i < 5; i++) {
            hold("guest-key-" + (200 + i), 1, "2026-12-29", "g" + i + "@example.com").andExpect(status().isCreated());
        }
        CLOCK.advance(Duration.ofMinutes(20));
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> runs = new ArrayList<>();
        try (var servers = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int s = 0; s < 4; s++) {
                runs.add(servers.submit(() -> {
                    start.await();
                    return holds.expireDue();
                }));
            }
            start.countDown();
        }
        assertThat(runs.stream().mapToInt(Future::resultNow).sum()).isEqualTo(5);
        assertThat(held(1, "2026-12-29")).isZero();
        assertThat(holds.expireDue()).isZero();   // and again later: nothing left to do
    }
}
