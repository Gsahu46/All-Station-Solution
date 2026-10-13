package com.parkora.parking;

import java.util.Comparator;

/**
 * One parking slot. walkMetres is the walk from the slot to the ground-floor exit: each floor up adds a ramp,
 * each slot further along a row adds a few metres. "Nearest" means the smallest walk.
 */
public record Slot(String id, int floor, int number, SlotType type, int walkMetres) {

    /** Nearest first; two slots at the same distance are ordered by id, so the choice never depends on luck. */
    static final Comparator<Slot> NEAREST_FIRST = Comparator.comparingInt(Slot::walkMetres).thenComparing(Slot::id);
}
