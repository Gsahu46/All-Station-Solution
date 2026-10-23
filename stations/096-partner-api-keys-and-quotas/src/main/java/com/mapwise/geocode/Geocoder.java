package com.mapwise.geocode;

import org.springframework.stereotype.Component;

import java.util.Locale;
import java.util.Map;
import java.util.Optional;

/** Simulated: a lookup in a fixed list of places, standing in for Mapwise's real geocoder. */
@Component
class Geocoder {

    record Place(String address, double lat, double lng) {
    }

    private static final Map<String, Place> PLACES = Map.of(
            "mg road, bengaluru", new Place("MG Road, Bengaluru, Karnataka", 12.9756, 77.6050),
            "connaught place, new delhi", new Place("Connaught Place, New Delhi, Delhi", 28.6315, 77.2167),
            "marine drive, mumbai", new Place("Marine Drive, Mumbai, Maharashtra", 18.9440, 72.8230),
            "park street, kolkata", new Place("Park Street, Kolkata, West Bengal", 22.5530, 88.3520),
            "charminar, hyderabad", new Place("Charminar, Hyderabad, Telangana", 17.3616, 78.4747));

    Optional<Place> find(String address) {
        return Optional.ofNullable(PLACES.get(address.strip().replaceAll("\\s+", " ").toLowerCase(Locale.ROOT)));
    }
}
