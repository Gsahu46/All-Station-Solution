package com.kartwala.checkout;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * The checkout as it shipped, kept only in tests (registered as a bean by the trap test, so Spring proxies it as it
 * did in production). placeOrder is @Transactional. checkout, the method the controller called, is not, and it
 * calls placeOrder on "this": the proxy is never involved, so no transaction starts.
 */
class OldCheckoutService {

    private final JdbcClient jdbc;

    OldCheckoutService(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public long checkout(long customerId, List<CheckoutService.LineRequest> lines) {
        if (lines.isEmpty()) {
            throw new IllegalArgumentException("no lines");
        }
        return placeOrder(customerId, lines);   // self-invocation: @Transactional below does nothing here
    }

    @Transactional
    public long placeOrder(long customerId, List<CheckoutService.LineRequest> lines) {
        long orderId = jdbc.sql("INSERT INTO orders (customer_id, total_paise) VALUES (?, 100) RETURNING id").param(customerId).query(Long.class).single();
        jdbc.sql("INSERT INTO payments (order_id, amount_paise, status) VALUES (?, 100, 'CAPTURED')").param(orderId).update();   // paid first
        for (CheckoutService.LineRequest line : lines) {
            int reserved = jdbc.sql("UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?").params(line.quantity(), line.productId(), line.quantity()).update();
            if (reserved == 0) {
                throw new IllegalStateException("out of stock: product " + line.productId());
            }
            jdbc.sql("INSERT INTO reservations (order_id, product_id, quantity, unit_price_paise) VALUES (?, ?, ?, 100)").params(orderId, line.productId(), line.quantity()).update();
        }
        return orderId;
    }
}
