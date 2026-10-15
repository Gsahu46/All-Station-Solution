package com.tiffino.orders;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

@Repository
class OrderStore {

    record Order(String orderNumber, String outletId, long totalPaise) {
    }

    private final JdbcClient jdbc;
    private final OrderNumbers numbers;

    OrderStore(JdbcClient jdbc, OrderNumbers numbers) {
        this.jdbc = jdbc;
        this.numbers = numbers;
    }

    @Transactional
    Order place(String outletId, long totalPaise) {
        return jdbc.sql("""
                        INSERT INTO orders (order_number, outlet_id, total_paise) VALUES (:number, :outlet, :total)
                        RETURNING order_number, outlet_id, total_paise""")
                .param("number", numbers.next()).param("outlet", outletId).param("total", totalPaise)
                .query(Order.class).single();
    }

    Optional<Order> byNumber(String orderNumber) {
        return jdbc.sql("SELECT order_number, outlet_id, total_paise FROM orders WHERE order_number = :number")
                .param("number", orderNumber).query(Order.class).optional();
    }
}
