package com.kartwala.recent;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Recently viewed products, kept in this server's memory, with two limits so memory cannot grow without end:
 * each user keeps their last 10 products, and the server keeps at most 10,000 users (the least recently active
 * user is dropped first). Both limits are demo rules.
 *
 * One lock for the whole store: simple and correct. In access-order maps even reads change the order, so a
 * "reads don't need the lock" shortcut corrupts them (see the Review tab).
 *
 * This memory belongs to ONE server. With several servers, each has its own copy; see the trap.
 */
@Component
class RecentlyViewed {

    static final int PER_USER = 10;
    static final int MAX_USERS = 10_000;

    private final LruMap<Long, LruMap<Long, Boolean>> users = new LruMap<>(MAX_USERS);

    synchronized List<Long> record(long userId, long productId) {
        users.computeIfAbsent(userId, id -> new LruMap<>(PER_USER)).put(productId, Boolean.TRUE);
        return list(userId);
    }

    /** Newest first. A copy: the caller can keep it while the history changes. */
    synchronized List<Long> list(long userId) {
        LruMap<Long, Boolean> history = users.get(userId);
        if (history == null) {
            return List.of();
        }
        List<Long> newestFirst = new ArrayList<>(history.keySet());
        Collections.reverse(newestFirst);
        return newestFirst;
    }

    synchronized int userCount() {
        return users.size();
    }

    /** For tests only. */
    synchronized void clear() {
        users.clear();
    }
}
