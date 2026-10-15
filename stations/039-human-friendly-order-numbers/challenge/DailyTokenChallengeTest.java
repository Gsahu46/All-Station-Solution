package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: the kitchen screen calls out short tokens, 1, 2, 3…, starting again each day for each outlet. Keep one
 * counter row per outlet and day, and take the next value with a single atomic statement
 * (INSERT … ON CONFLICT … DO UPDATE … RETURNING), so parallel orders never share a token.
 */
class DailyTokenChallengeTest extends ApiTest {

    @Autowired
    DailyTokens tokens;

    @Test
    void fiftyOrdersAtOnceAtOneOutletGetTokensOneToFifty() throws Exception {
        LocalDate day = LocalDate.of(2026, 10, 15);
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> results = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 50; i++) {
                results.add(threads.submit(() -> {
                    start.await();
                    return tokens.next("TF-11", day);
                }));
            }
            start.countDown();
        }
        List<Integer> issued = new ArrayList<>();
        for (Future<Integer> f : results) {
            issued.add(f.get());
        }
        assertThat(issued).containsExactlyInAnyOrderElementsOf(java.util.stream.IntStream.rangeClosed(1, 50).boxed().toList());
    }

    @Test
    void eachOutletAndEachDayStartsAtOne() {
        LocalDate day = LocalDate.of(2026, 10, 16);
        assertThat(tokens.next("TF-12", day)).isEqualTo(1);
        assertThat(tokens.next("TF-12", day)).isEqualTo(2);
        assertThat(tokens.next("TF-13", day)).isEqualTo(1);
        assertThat(tokens.next("TF-12", day.plusDays(1))).isEqualTo(1);
    }

    @Test
    void anOrderShowsItsToken() throws Exception {
        place("""
                {"outletId":"TF-14","totalPaise":45000}""").andExpect(jsonPath("$.token").value(1));
        place("""
                {"outletId":"TF-14","totalPaise":45000}""").andExpect(jsonPath("$.token").value(2));
    }
}
