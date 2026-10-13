package com.chaupal.comments;

import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * At most 5 comments per user in any 60 seconds (a demo rule). Each user has a queue of recent comment times;
 * times older than the window drop off the front. In memory, so it works for one server only.
 */
@Component
class RateLimiter {

    static final int LIMIT = 5;
    static final Duration WINDOW = Duration.ofSeconds(60);
    private final Map<String, Deque<Instant>> recent = new ConcurrentHashMap<>();

    /** True and counted if the user may post now; false if they have used up the window. */
    boolean tryAcquire(String user) {
        Instant now = Instant.now();
        Deque<Instant> times = recent.computeIfAbsent(user, u -> new ArrayDeque<>());
        synchronized (times) {
            while (!times.isEmpty() && times.peekFirst().isBefore(now.minus(WINDOW))) {
                times.pollFirst();
            }
            if (times.size() >= LIMIT) {
                return false;
            }
            times.addLast(now);
            return true;
        }
    }

    /** For tests only. */
    void reset() {
        recent.clear();
    }
}
