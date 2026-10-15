package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/** 100 orders placed at the same instant, as at the lunch rush: 100 different numbers, every one valid, no failures. */
class OrderNumberConcurrencyTest extends ApiTest {

    @Test
    void aHundredOrdersAtOnceGetAHundredDifferentNumbers() throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        ConcurrentLinkedQueue<Throwable> failures = new ConcurrentLinkedQueue<>();
        List<Future<String>> numbers = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 100; i++) {
                numbers.add(threads.submit(() -> {
                    start.await();
                    try {
                        return store.place("TF-07", 45_000).orderNumber();
                    } catch (RuntimeException e) {
                        failures.add(e);
                        return null;
                    }
                }));
            }
            start.countDown();
        }
        List<String> issued = new ArrayList<>();
        for (Future<String> f : numbers) {
            issued.add(f.get());
        }
        assertThat(failures).isEmpty();
        assertThat(issued).doesNotHaveDuplicates().allMatch(n -> n.matches(ORDER_NUMBER) && OrderNumbers.checkDigitMatches(n));
        assertThat(orders()).isEqualTo(100);
    }
}
