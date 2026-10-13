package com.kartwala.recent;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Challenge 1 adds remove; challenge 2 stores when each product was viewed, and hides views older than 30 days.
 * Old entries are not deleted on read: they fall out through the LRU limit, so reading stays cheap.
 */
@Component
class RecentlyViewed {

    static final int PER_USER = 10;
    static final int MAX_USERS = 10_000;
    static final Duration KEEP = Duration.ofDays(30);

    private final LruMap<Long, LruMap<Long, Instant>> users = new LruMap<>(MAX_USERS);
    private final Clock clock;

    /** The station's tests build the store without Spring. */
    RecentlyViewed() {
        this(Clock.systemUTC());
    }

    @Autowired
    RecentlyViewed(Clock clock) {
        this.clock = clock;
    }

    synchronized List<Long> record(long userId, long productId) {
        users.computeIfAbsent(userId, id -> new LruMap<>(PER_USER)).put(productId, clock.instant());
        return list(userId);
    }

    synchronized List<Long> list(long userId) {
        LruMap<Long, Instant> history = users.get(userId);
        if (history == null) {
            return List.of();
        }
        Instant oldest = clock.instant().minus(KEEP);
        List<Long> newestFirst = new ArrayList<>();
        for (Map.Entry<Long, Instant> e : history.entrySet()) {
            if (e.getValue().isAfter(oldest)) {
                newestFirst.addFirst(e.getKey());
            }
        }
        return newestFirst;
    }

    /** Challenge 1. Removing what is not there is fine: the result is the same. */
    synchronized void remove(long userId, long productId) {
        LruMap<Long, Instant> history = users.get(userId);
        if (history != null) {
            history.remove(productId);
        }
    }

    synchronized int userCount() {
        return users.size();
    }

    synchronized void clear() {
        users.clear();
    }
}
