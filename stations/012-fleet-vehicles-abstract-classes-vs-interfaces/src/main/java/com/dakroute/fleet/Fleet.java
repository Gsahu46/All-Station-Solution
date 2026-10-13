package com.dakroute.fleet;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;

/** Dakroute's vehicles. Fixed for this station; a fleet database comes later. */
@Component
class Fleet {

    private final Map<Long, Vehicle> vehicles = Map.of(
            1L, new Vehicle(1, "KA01TR1234", "Tata Prima 2830.K", Powertrain.DIESEL, Body.TRUCK, 128_400),
            2L, new Vehicle(2, "KA01VN5678", "Mahindra Supro", Powertrain.PETROL, Body.VAN, 42_300),
            3L, new Vehicle(3, "KA01EV9012", "Tata Ace EV", Powertrain.ELECTRIC, Body.VAN, 18_950),
            4L, new Vehicle(4, "KA01BK3456", "Hero Splendor+", Powertrain.PETROL, Body.TWO_WHEELER, 9_600),
            5L, new Vehicle(5, "KA01EB7890", "Ather Rizta", Powertrain.ELECTRIC, Body.TWO_WHEELER, 3_200));

    Optional<Vehicle> find(long id) {
        return Optional.ofNullable(vehicles.get(id));
    }
}
