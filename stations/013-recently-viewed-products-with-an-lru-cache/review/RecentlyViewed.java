package com.kartwala.recent;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Recently viewed products. ConcurrentHashMap makes it thread-safe, so no synchronized needed (faster). */
@Component
class RecentlyViewed {

    static final int PER_USER = 10;
    static final int MAX_USERS = 10_000;

    private final Map<Long, LruMap<Long, Boolean>> users = new ConcurrentHashMap<>();

    List<Long> record(long userId, long productId) {
        users.computeIfAbsent(userId, id -> new LruMap<>(PER_USER)).put(productId, Boolean.TRUE);
        return list(userId);
    }

    List<Long> list(long userId) {
        LruMap<Long, Boolean> history = users.get(userId);
        if (history == null) {
            return List.of();
        }
        List<Long> newestFirst = new ArrayList<>(history.keySet());
        Collections.reverse(newestFirst);
        return newestFirst;
    }

    int userCount() {
        return users.size();
    }

    void clear() {
        users.clear();
    }
}
