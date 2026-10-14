package com.tijori.otp;

import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * At most MAX requests per number in any WINDOW (demo rule: 3 in 10 minutes). The check and the booking happen in
 * one ConcurrentHashMap.compute call, which is atomic per key: two requests for one number cannot both see "2 used"
 * and both book the third slot. Requests for different numbers do not wait for each other.
 *
 * Limit: this map lives in one server's memory. With N servers behind a load balancer, a number can get N x MAX.
 * Safe while one instance runs; across servers the count needs a shared store (station 125).
 */
@Component
class OtpLimiter {

    static final int MAX = 3;
    static final Duration WINDOW = Duration.ofMinutes(10);

    /** accepted: whether a slot was booked; attemptsLeft after this one; retryAfter until a slot frees, if refused. */
    record Decision(boolean accepted, int attemptsLeft, Duration retryAfter) {
    }

    private final Clock clock;
    private final Map<String, Deque<Instant>> windows = new ConcurrentHashMap<>();

    OtpLimiter(Clock clock) {
        this.clock = clock;
    }

    Decision tryAcquire(String mobile) {
        Instant now = clock.instant();
        Decision[] decision = new Decision[1];
        windows.compute(mobile, (m, times) -> {
            Deque<Instant> window = times == null ? new ArrayDeque<>() : times;
            while (!window.isEmpty() && !window.peekFirst().isAfter(now.minus(WINDOW))) {
                window.pollFirst();   // older than the window: no longer counts
            }
            if (window.size() >= MAX) {
                decision[0] = new Decision(false, 0, Duration.between(now, window.peekFirst().plus(WINDOW)));
            } else {
                window.addLast(now);
                decision[0] = new Decision(true, MAX - window.size(), Duration.ZERO);
            }
            return window;
        });
        return decision[0];
    }

    void clear() {
        windows.clear();
    }
}
