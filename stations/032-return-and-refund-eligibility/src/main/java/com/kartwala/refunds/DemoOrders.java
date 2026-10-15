package com.kartwala.refunds;

import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.LocalDate;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/** Demo orders, delivered a fixed number of days before the app started, so examples read the same any day. */
@Component
class DemoOrders implements OrderLookup {

    private final Map<String, Order> byId;

    DemoOrders(Clock clock) {
        LocalDate today = RefundService.today(clock);
        byId = Stream.of(
                new Order("KW-1001", "Cotton kurta", Category.CLOTHING, 129_900, today.minusDays(14), false),
                new Order("KW-1002", "Innerwear pack", Category.CLOTHING, 49_900, today.minusDays(3), true),
                new Order("KW-1003", "Wireless earbuds", Category.ELECTRONICS, 249_900, today.minusDays(9), false),
                new Order("KW-1004", "Smartphone", Category.ELECTRONICS, 1_899_900, today.minusDays(2), false),
                new Order("KW-1005", "Grocery basket", Category.GROCERY, 65_000, today.minusDays(1), false),
                new Order("KW-1006", "Novel", Category.BOOKS, 39_900, null, false)
        ).collect(Collectors.toUnmodifiableMap(Order::id, Function.identity()));
    }

    @Override
    public Optional<Order> find(String orderId) {
        return Optional.ofNullable(byId.get(orderId));
    }
}
