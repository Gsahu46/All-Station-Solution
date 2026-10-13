package com.kartwala.recent;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** The LRU rules on their own: access order, eviction, and the bound on the number of users. */
class LruMapTest {

    @Test
    void theLeastRecentlyUsedEntryIsEvicted() {
        LruMap<String, Integer> lru = new LruMap<>(3);
        lru.put("a", 1);
        lru.put("b", 2);
        lru.put("c", 3);
        lru.get("a");          // in access order, reading counts as using
        lru.put("d", 4);       // so "b", untouched the longest, goes
        assertThat(lru.keySet()).containsExactly("c", "a", "d");
    }

    @Test
    void theServerKeepsAtMostMaxUsersAndDropsTheLeastRecentlyActive() {
        RecentlyViewed store = new RecentlyViewed();
        for (long user = 1; user <= RecentlyViewed.MAX_USERS + 5; user++) {
            store.record(user, 1);
        }
        assertThat(store.userCount()).isEqualTo(RecentlyViewed.MAX_USERS);
        assertThat(store.list(1)).isEmpty();                       // users 1..5 were dropped
        assertThat(store.list(RecentlyViewed.MAX_USERS + 5)).containsExactly(1L);
    }

    @Test
    void aReturnedListDoesNotChangeAfterwards() {
        RecentlyViewed store = new RecentlyViewed();
        store.record(7, 1);
        List<Long> before = store.list(7);
        store.record(7, 2);
        assertThat(before).containsExactly(1L);
    }
}
