package com.kartwala.checkout;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the app on a real PostgreSQL, no orders before each test, stock reset: Assam tea (1) 50, Kashmiri
 * chilli (2) 5, steel tiffin box (3) 0.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void freshShop() {
        jdbc.sql("TRUNCATE payments, reservations, orders RESTART IDENTITY").update();
        jdbc.sql("UPDATE products SET stock = CASE id WHEN 1 THEN 50 WHEN 2 THEN 5 ELSE 0 END").update();
    }

    ResultActions checkout(String lines) throws Exception {
        return mvc.perform(post("/checkouts").contentType(MediaType.APPLICATION_JSON).content("{\"customerId\":7,\"lines\":" + lines + "}"));
    }

    /** "orders/reservations/payments/tea stock/chilli stock", one string to compare. */
    String state() {
        return jdbc.sql("""
                SELECT (SELECT count(*) FROM orders) || '/' || (SELECT count(*) FROM reservations) || '/' || (SELECT count(*) FROM payments)
                    || '/' || (SELECT stock FROM products WHERE id = 1) || '/' || (SELECT stock FROM products WHERE id = 2)""").query(String.class).single();
    }
}
