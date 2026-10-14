package com.tiffino.orders;

import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Orders in memory (demo data), and the one place a status changes. Each change is a single compute() on the order:
 * check the table and write the new status as one step, so two tablets tapping at once cannot both win.
 */
@Component
class Orders {

    record Change(OrderStatus status, Instant at) {
    }

    record Order(long id, String restaurant, OrderStatus status, List<Change> history) {
    }

    /** A move the table does not allow, with what is allowed instead. */
    static final class IllegalMove extends RuntimeException {
        final OrderStatus from;
        final OrderStatus to;

        IllegalMove(long id, OrderStatus from, OrderStatus to) {
            super("Order " + id + " cannot go from " + from + " to " + to + ".");
            this.from = from;
            this.to = to;
        }
    }

    private final Clock clock;
    private final Map<Long, Order> byId = new ConcurrentHashMap<>();

    Orders(Clock clock) {
        this.clock = clock;
        reset();
    }

    Optional<Order> find(long id) {
        return Optional.ofNullable(byId.get(id));
    }

    /**
     * Moves the order, or throws IllegalMove. Asking for the status it already has is not a move: the order comes
     * back unchanged (a tablet double tap, or a retry after a timeout).
     */
    Optional<Order> move(long id, OrderStatus to) {
        return Optional.ofNullable(byId.computeIfPresent(id, (key, order) -> {
            if (order.status() == to) {
                return order;
            }
            if (!order.status().canMoveTo(to)) {
                throw new IllegalMove(id, order.status(), to);
            }
            List<Change> history = new java.util.ArrayList<>(order.history());
            history.add(new Change(to, clock.instant().truncatedTo(java.time.temporal.ChronoUnit.SECONDS)));
            return new Order(id, order.restaurant(), to, List.copyOf(history));
        }));
    }

    /** Demo orders: one just placed, one cancelled, one being prepared. Also used by tests to start clean. */
    void reset() {
        byId.clear();
        Instant now = clock.instant().truncatedTo(java.time.temporal.ChronoUnit.SECONDS);
        byId.put(1001L, new Order(1001, "Annapoorna Mess", OrderStatus.PLACED, List.of(new Change(OrderStatus.PLACED, now))));
        byId.put(1002L, new Order(1002, "Annapoorna Mess", OrderStatus.CANCELLED,
                List.of(new Change(OrderStatus.PLACED, now), new Change(OrderStatus.CANCELLED, now))));
        byId.put(1003L, new Order(1003, "Biryani Point", OrderStatus.PREPARING, List.of(new Change(OrderStatus.PLACED, now),
                new Change(OrderStatus.ACCEPTED, now), new Change(OrderStatus.PREPARING, now))));
    }
}
