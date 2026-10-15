package com.tiffino.orders;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.Optional;
import java.util.UUID;

@Repository
class OrderStore {

    record Order(UUID orderId, String orderNumber, Integer token, String outletId, long totalPaise) {
    }

    private static final String COLUMNS = "public_id AS order_id, order_number, token, outlet_id, total_paise";

    private final JdbcClient jdbc;
    private final OrderNumbers numbers;
    private final DailyTokens tokens;

    OrderStore(JdbcClient jdbc, OrderNumbers numbers, DailyTokens tokens) {
        this.jdbc = jdbc;
        this.numbers = numbers;
        this.tokens = tokens;
    }

    @Transactional
    Order place(String outletId, long totalPaise) {
        int token = tokens.next(outletId, LocalDate.now(ZoneId.of("Asia/Kolkata")));
        return jdbc.sql("INSERT INTO orders (order_number, token, outlet_id, total_paise) VALUES (:number, :token, :outlet, :total) RETURNING " + COLUMNS)
                .param("number", numbers.next()).param("token", token).param("outlet", outletId).param("total", totalPaise)
                .query(Order.class).single();
    }

    Optional<Order> byNumber(String orderNumber) {
        return jdbc.sql("SELECT " + COLUMNS + " FROM orders WHERE order_number = :number").param("number", orderNumber).query(Order.class).optional();
    }

    Optional<Order> byId(UUID orderId) {
        return jdbc.sql("SELECT " + COLUMNS + " FROM orders WHERE public_id = :id").param("id", orderId).query(Order.class).optional();
    }
}
