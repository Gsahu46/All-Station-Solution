package com.kartwala.recent;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Concurrency: many requests at the same moment, released together on virtual threads, as a busy sale page sends them.
 * The invariants: every request succeeds, a history never exceeds 10, never holds a duplicate.
 * The timeout stops the build if a broken map ever loops forever.
 */
@Timeout(value = 60, threadMode = Timeout.ThreadMode.SEPARATE_THREAD)
class RecentlyViewedConcurrencyTest extends ApiTest {

    /** Runs each task on its own virtual thread; all wait at the start line, then go at once. Returns the HTTP statuses. */
    private List<Integer> together(List<Callable> tasks) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {
            List<Future<Integer>> results = new ArrayList<>();
            for (Callable task : tasks) {
                results.add(pool.submit(() -> {
                    start.await();
                    return task.call();
                }));
            }
            start.countDown();
            List<Integer> statuses = new ArrayList<>();
            for (Future<Integer> f : results) {
                statuses.add(f.get());
            }
            return statuses;
        }
    }

    interface Callable {
        int call() throws Exception;
    }

    @Test
    void twoHundredViewsByOneUserAtOnceLeaveTenDistinctProducts() throws Exception {
        List<Callable> tasks = new ArrayList<>();
        for (long p = 1; p <= 200; p++) {
            long product = p;
            tasks.add(() -> view(7, product).andReturn().getResponse().getStatus());
        }
        assertThat(together(tasks)).containsOnly(200);
        List<Long> history = recentlyViewed.list(7);
        assertThat(history).hasSize(10).doesNotHaveDuplicates().allMatch(p -> p >= 1 && p <= 200);
    }

    @Test
    void readsAndWritesForManyUsersAtOnceNeverBreakTheLimits() throws Exception {
        List<Callable> tasks = new ArrayList<>();
        for (int i = 0; i < 1_000; i++) {
            long user = i % 50, product = i % 37;
            tasks.add(i % 3 == 0
                    ? () -> mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                            .get("/users/{id}/recently-viewed", user + 1)).andReturn().getResponse().getStatus()
                    : () -> view(user + 1, product + 1).andReturn().getResponse().getStatus());
        }
        assertThat(together(tasks)).containsOnly(200);
        for (long user = 1; user <= 50; user++) {
            List<Long> h = recentlyViewed.list(user);
            assertThat(h.size()).isLessThanOrEqualTo(10);
            assertThat(new HashSet<>(h)).hasSameSizeAs(h);
        }
    }
}
