package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.util.ArrayDeque;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;

import static com.tiffino.orders.OrderStatus.*;
import static org.assertj.core.api.Assertions.assertThat;

/** The table itself: every pair checked against the rule written out by hand, and two moves racing. */
class TransitionTableTest {

    /** The business rule, written independently of the code. */
    static final Map<OrderStatus, Set<OrderStatus>> EXPECTED = Map.of(
            PLACED, EnumSet.of(ACCEPTED, REJECTED, CANCELLED),
            ACCEPTED, EnumSet.of(PREPARING, CANCELLED),
            PREPARING, EnumSet.of(READY_FOR_PICKUP),
            READY_FOR_PICKUP, EnumSet.of(PICKED_UP),
            PICKED_UP, EnumSet.of(DELIVERED),
            DELIVERED, EnumSet.noneOf(OrderStatus.class),
            CANCELLED, EnumSet.noneOf(OrderStatus.class),
            REJECTED, EnumSet.noneOf(OrderStatus.class));

    @Test
    void everyPairOfStatusesMatchesTheRule() {
        for (OrderStatus from : OrderStatus.values()) {
            for (OrderStatus to : OrderStatus.values()) {
                assertThat(from.canMoveTo(to)).as(from + " -> " + to).isEqualTo(EXPECTED.get(from).contains(to));
            }
        }
    }

    @Test
    void everyStatusIsReachableFromPlacedAndOnlyEndsHaveNoWayOut() {
        Set<OrderStatus> seen = EnumSet.of(PLACED);
        ArrayDeque<OrderStatus> todo = new ArrayDeque<>(List.of(PLACED));
        while (!todo.isEmpty()) {
            for (OrderStatus next : todo.poll().next()) {
                if (seen.add(next)) {
                    todo.add(next);
                }
            }
        }
        assertThat(seen).containsExactlyInAnyOrder(OrderStatus.values());
        assertThat(EnumSet.allOf(OrderStatus.class).stream().filter(OrderStatus::isTerminal)).containsExactlyInAnyOrder(DELIVERED, CANCELLED, REJECTED);
    }

    @Test
    void whenTheKitchenAndTheCustomerTapAtOnceExactlyOneWins() throws Exception {
        for (int round = 0; round < 50; round++) {
            Orders orders = new Orders(Clock.systemUTC());
            orders.move(1001, ACCEPTED);
            Map<OrderStatus, Boolean> won = new ConcurrentHashMap<>();
            CountDownLatch start = new CountDownLatch(1);
            try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
                for (OrderStatus to : List.of(PREPARING, CANCELLED)) {
                    threads.submit(() -> {
                        start.await();
                        try {
                            orders.move(1001, to);
                            won.put(to, true);
                        } catch (Orders.IllegalMove lost) {
                            won.put(to, false);
                        }
                        return null;
                    });
                }
                start.countDown();
            }
            assertThat(won.values()).as("round " + round).containsExactlyInAnyOrder(true, false);
            OrderStatus winner = won.get(PREPARING) ? PREPARING : CANCELLED;
            assertThat(orders.find(1001).orElseThrow().status()).isEqualTo(winner);
            assertThat(orders.find(1001).orElseThrow().history()).hasSize(3);
        }
    }
}
