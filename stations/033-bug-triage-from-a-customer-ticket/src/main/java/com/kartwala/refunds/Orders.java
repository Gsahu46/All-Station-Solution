package com.kartwala.refunds;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/** Demo orders in memory. KW-1042 is the order from the customer's ticket: no coupon. */
@Component
class Orders {

    private final Map<String, Order> byId = Map.of(
            "KW-1041", new Order("KW-1041", List.of(
                    new Line("L1", "Cotton kurta", 129_900),
                    new Line("L2", "Dupatta", 49_900)), new Coupon("FEST200", 20_000)),
            "KW-1042", new Order("KW-1042", List.of(
                    new Line("L1", "Denim jeans", 199_900),
                    new Line("L2", "Leather belt", 59_900)), null));

    Optional<Order> find(String orderId) {
        return Optional.ofNullable(byId.get(orderId));
    }
}
