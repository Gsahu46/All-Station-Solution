package com.kartwala.wishlist;

import org.springframework.stereotype.Component;

import java.util.HashMap;
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

    /** Challenge 1: the whole list in one step, under one lock. Set.addAll skips what is already there. */
    synchronized void addAll(long id, List<Sku> skus) {
        lists.get(id).addAll(skus);
    }

    /** Challenge 2: Sku -> number of wishlists that hold it. A HashMap keyed by a record works because of value equality. */
    synchronized Map<Sku, Integer> counts() {
        Map<Sku, Integer> counts = new HashMap<>();
        lists.values().forEach(list -> list.forEach(sku -> counts.merge(sku, 1, Integer::sum)));
        return counts;
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
