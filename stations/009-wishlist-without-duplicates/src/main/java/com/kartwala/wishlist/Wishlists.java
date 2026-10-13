package com.kartwala.wishlist;

import org.springframework.stereotype.Component;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Each wishlist is a LinkedHashSet of Skus: a set, so a Sku can be in it once; linked, so it keeps the order
 * items were added. In memory; synchronized so two requests do not interleave.
 */
@Component
class Wishlists {

    private final Map<Long, Set<Sku>> lists = Map.of(7L, new LinkedHashSet<>(), 8L, new LinkedHashSet<>());

    boolean exists(long id) {
        return lists.containsKey(id);
    }

    /** True if the Sku was added, false if it was already there. Set.add tells us: no separate contains() check. */
    synchronized boolean add(long id, Sku sku) {
        return lists.get(id).add(sku);
    }

    synchronized void remove(long id, Sku sku) {
        lists.get(id).remove(sku);
    }

    synchronized Optional<List<Sku>> items(long id) {
        return Optional.ofNullable(lists.get(id)).map(List::copyOf);
    }

    /** For tests only. */
    synchronized void clear() {
        lists.values().forEach(Set::clear);
    }
}
