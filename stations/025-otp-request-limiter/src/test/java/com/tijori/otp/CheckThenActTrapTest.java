package com.tijori.otp;

import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: it reproduces the bug before the fix, and states the fix's limit. */
class CheckThenActTrapTest {

    /**
     * The "before" limiter: check the count, send the SMS, then record the request. Each step is thread-safe on its
     * own (a ConcurrentHashMap, a synchronized list); the sequence is not. Kept only in tests.
     */
    static final class OldLimiter {
        final Map<String, List<Instant>> sent = new ConcurrentHashMap<>();

        boolean request(String mobile) throws InterruptedException {
            List<Instant> times = sent.computeIfAbsent(mobile, m -> java.util.Collections.synchronizedList(new ArrayList<>()));
            if (times.size() >= 3) {
                return false;
            }
            Thread.sleep(50);              // the SMS provider call
            times.add(Instant.now());
            return true;
        }
    }

    static int acceptedOutOf20(java.util.function.Predicate<String> request) throws Exception {
        AtomicInteger accepted = new AtomicInteger();
        CountDownLatch start = new CountDownLatch(1);
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 20; i++) {
                threads.submit(() -> {
                    start.await();
                    if (request.test("9876543210")) {
                        accepted.incrementAndGet();
                    }
                    return null;
                });
            }
            start.countDown();   // all 20 at the same instant, like a bot
        }
        return accepted.get();
    }

    @Test
    void theOldLimiterLetsTwentyThroughWhenTheyArriveTogether() throws Exception {
        OldLimiter old = new OldLimiter();
        int accepted = acceptedOutOf20(m -> {
            try {
                return old.request(m);
            } catch (InterruptedException e) {
                throw new IllegalStateException(e);
            }
        });
        assertThat(accepted).isGreaterThan(3);   // every one checked "fewer than 3 sent" before any was recorded
    }

    @Test
    void theAtomicLimiterLetsExactlyThreeThrough() throws Exception {
        OtpLimiter limiter = new OtpLimiter(Clock.systemUTC());
        assertThat(acceptedOutOf20(m -> limiter.tryAcquire(m).accepted())).isEqualTo(3);
    }

    @Test
    void theLimitIsPerServerSoTwoServersAllowSix() throws Exception {
        // The known limit of an in-memory count: each server keeps its own. Station 125 shares the count.
        OtpLimiter serverA = new OtpLimiter(Clock.systemUTC());
        OtpLimiter serverB = new OtpLimiter(Clock.systemUTC());
        AtomicInteger turn = new AtomicInteger();
        int accepted = acceptedOutOf20(m -> (turn.getAndIncrement() % 2 == 0 ? serverA : serverB).tryAcquire(m).accepted());
        assertThat(accepted).isEqualTo(6);
    }
}
