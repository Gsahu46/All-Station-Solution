package com.dakroute.fleet;

import java.util.List;

/**
 * Composition: a vehicle HAS a powertrain and a body; it does not inherit from them. A new kind of vehicle is a new
 * combination of parts, not a new class at the bottom of a family tree.
 */
public record Vehicle(long id, String registration, String model, Powertrain powertrain, Body body, int odometerKm) {

    /** Polymorphism: the planner asks every part for its tasks without knowing which part it is. */
    List<ServiceItems> parts() {
        return List.of(powertrain, body);
    }
}
