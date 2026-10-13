package com.tiffino.addresses;

import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Each customer's addresses, keyed by label. A map, not a list: putting "home" again replaces "home",
 * so a repeated request cannot create a second one. In memory; synchronized so two requests do not interleave.
 */
@Component
class AddressBook {

    static final int MAX_ADDRESSES = 10;
    private final Set<Long> customers = Set.of(42L, 43L);
    private final Map<Long, Map<String, Address>> books = new LinkedHashMap<>();

    boolean customerExists(long customerId) {
        return customers.contains(customerId);
    }

    synchronized Optional<Address> get(long customerId, String label) {
        return Optional.ofNullable(book(customerId).get(label));
    }

    synchronized Map<String, Address> all(long customerId) {
        return Map.copyOf(book(customerId));
    }

    /** What a PUT did. The controller turns it into 201, 200 or 409. */
    enum PutResult { CREATED, REPLACED, FULL }

    synchronized PutResult put(long customerId, String label, Address address) {
        Map<String, Address> book = book(customerId);
        if (!book.containsKey(label) && book.size() >= MAX_ADDRESSES) {
            return PutResult.FULL;
        }
        return book.put(label, address) == null ? PutResult.CREATED : PutResult.REPLACED;
    }

    /** Removes the address if it is there. Removing something already gone is not an error. */
    synchronized void delete(long customerId, String label) {
        book(customerId).remove(label);
    }

    /** For tests only. */
    synchronized void clear() {
        books.clear();
    }

    private Map<String, Address> book(long customerId) {
        return books.computeIfAbsent(customerId, id -> new LinkedHashMap<>());
    }
}
