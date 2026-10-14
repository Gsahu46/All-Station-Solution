package com.tiffino.orders;

import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

/**
 * An order's life as a state machine. The transition table is the whole rule: a move not in it is refused,
 * whoever asks. Terminal statuses (DELIVERED, CANCELLED, REJECTED) have no way out.
 */
enum OrderStatus {
    PLACED, ACCEPTED, REJECTED, PREPARING, READY_FOR_PICKUP, PICKED_UP, DELIVERED, CANCELLED;

    private static final Map<OrderStatus, Set<OrderStatus>> NEXT = new EnumMap<>(OrderStatus.class);

    static {
        NEXT.put(PLACED, EnumSet.of(ACCEPTED, REJECTED, CANCELLED));
        NEXT.put(ACCEPTED, EnumSet.of(PREPARING, CANCELLED));
        NEXT.put(PREPARING, EnumSet.of(READY_FOR_PICKUP));
        NEXT.put(READY_FOR_PICKUP, EnumSet.of(PICKED_UP));
        NEXT.put(PICKED_UP, EnumSet.of(DELIVERED));
        NEXT.put(DELIVERED, EnumSet.noneOf(OrderStatus.class));
        NEXT.put(CANCELLED, EnumSet.noneOf(OrderStatus.class));
        NEXT.put(REJECTED, EnumSet.noneOf(OrderStatus.class));
    }

    Set<OrderStatus> next() {
        return NEXT.get(this);
    }

    boolean canMoveTo(OrderStatus to) {
        return NEXT.get(this).contains(to);
    }

    boolean isTerminal() {
        return NEXT.get(this).isEmpty();
    }
}
