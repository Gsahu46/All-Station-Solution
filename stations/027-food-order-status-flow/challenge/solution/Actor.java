package com.tiffino.orders;

import java.util.EnumSet;
import java.util.Set;

/** Challenge 1: who may move an order to which status. An enum with data: each party carries its own moves. */
enum Actor {
    RESTAURANT(EnumSet.of(OrderStatus.ACCEPTED, OrderStatus.REJECTED, OrderStatus.PREPARING, OrderStatus.READY_FOR_PICKUP, OrderStatus.CANCELLED)),
    RIDER(EnumSet.of(OrderStatus.PICKED_UP, OrderStatus.DELIVERED)),
    CUSTOMER(EnumSet.of(OrderStatus.CANCELLED));

    private final Set<OrderStatus> mayMoveTo;

    Actor(Set<OrderStatus> mayMoveTo) {
        this.mayMoveTo = mayMoveTo;
    }

    boolean mayMoveTo(OrderStatus to) {
        return mayMoveTo.contains(to);
    }
}
