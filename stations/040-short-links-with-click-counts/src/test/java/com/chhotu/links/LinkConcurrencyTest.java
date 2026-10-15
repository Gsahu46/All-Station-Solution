package com.chhotu.links;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** A campaign SMS goes out and everyone taps at once. Every click counts, and every new link gets its own code. */
class LinkConcurrencyTest extends ApiTest {

    /** Runs n copies of the task on virtual threads, all released together by one latch. */
    static <T> List<T> together(int n, Callable<T> task) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<T>> futures = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < n; i++) {
                futures.add(threads.submit(() -> {
                    start.await();
                    return task.call();
                }));
            }
            start.countDown();
        }
        List<T> results = new ArrayList<>();
        for (Future<T> f : futures) {
            results.add(f.get());
        }
        return results;
    }

    @Test
    void aThousandClicksAtOnceAreAThousandClicks() throws Exception {
        String code = links.create("https://shop.example/diwali-sale").orElseThrow();
        List<Integer> statuses = together(1_000, () -> follow(code).andReturn().getResponse().getStatus());
        assertThat(statuses).containsOnly(302);
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/links/{c}/stats", code))
                .andExpect(jsonPath("$.clicks").value(1000));   // stored plus not yet flushed
        clicks.flush();
        assertThat(storedClicks(code)).isEqualTo(1_000);
    }

    @Test
    void clicksArrivingDuringAFlushAreKeptForTheNextOne() throws Exception {
        String code = links.create("https://shop.example/diwali-sale").orElseThrow();
        AtomicBoolean clicking = new AtomicBoolean(true);
        Thread flusher = Thread.ofVirtual().start(() -> {
            while (clicking.get()) {
                clicks.flush();
            }
        });
        together(2_000, () -> follow(code).andReturn().getResponse().getStatus());
        clicking.set(false);
        flusher.join();
        clicks.flush();
        assertThat(storedClicks(code)).isEqualTo(2_000);
    }

    @Test
    void theFirstClicksOnANewLinkAreNotLost() throws Exception {
        // The moment a link gets its first clicks is when its counter is created: 200 taps on 50 fresh links.
        for (int round = 0; round < 50; round++) {
            String code = "Fresh" + String.format("%02d", round);
            together(200, () -> {
                clicks.record(code);
                return null;
            });
            assertThat(clicks.pending(code)).as(code).isEqualTo(200);
        }
    }

    @Test
    void twoHundredLinksAtOnceGetTwoHundredCodes() throws Exception {
        List<String> codes = together(200, () -> links.create("https://example.com/" + Thread.currentThread().threadId()).orElseThrow());
        Set<String> distinct = new HashSet<>(codes);
        assertThat(distinct).hasSize(200).allMatch(c -> c.matches("[0-9A-Za-z]{7}"));
        assertThat(jdbc.sql("SELECT count(*) FROM links").query(Long.class).single()).isEqualTo(200);
    }
}
