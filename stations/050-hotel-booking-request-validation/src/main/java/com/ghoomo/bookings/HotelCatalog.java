package com.ghoomo.bookings;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;

/** Demo catalogue (invented hotels): room types and how many guests each sleeps. A real one lives in a database. */
@Component
class HotelCatalog {

    record Hotel(long id, String name, Map<String, Integer> sleeps) {
    }

    private static final Map<Long, Hotel> HOTELS = Map.of(
            1L, new Hotel(1, "Ghoomo Inn, Jaipur", Map.of("STANDARD", 2, "DELUXE", 3, "FAMILY", 4)),
            2L, new Hotel(2, "Ghoomo Stays, Goa", Map.of("DORM_BED", 1, "STANDARD", 2)));

    Optional<Hotel> find(long id) {
        return Optional.ofNullable(HOTELS.get(id));
    }

    /** Room types are identifiers: compared upper-case in Locale.ROOT, so "family" works on every server locale. */
    static String roomType(String raw) {
        return raw.strip().toUpperCase(java.util.Locale.ROOT);
    }
}
