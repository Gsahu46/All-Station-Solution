package com.mapwise.edge;

import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Challenge 2: at most 3 uploads a minute per client address (demo rule), a sliding window per address.
 * shortcut: in memory and never cleaned up; with many clients, expire idle addresses or keep this in Valkey.
 */
@Component
class UploadLimiter {

    static final int PER_MINUTE = 3;
    private final Map<String, Deque<Instant>> recent = new ConcurrentHashMap<>();

    /** 0 when allowed, else the seconds to wait. */
    long take(String clientIp) {
        Instant now = Instant.now();
        Deque<Instant> times = recent.computeIfAbsent(clientIp, ip -> new ArrayDeque<>());
        synchronized (times) {
            while (!times.isEmpty() && times.peekFirst().isBefore(now.minus(Duration.ofMinutes(1)))) {
                times.pollFirst();
            }
            if (times.size() >= PER_MINUTE) {
                return Math.max(1, Duration.between(now, times.peekFirst().plus(Duration.ofMinutes(1))).toSeconds());
            }
            times.addLast(now);
            return 0;
        }
    }
}
