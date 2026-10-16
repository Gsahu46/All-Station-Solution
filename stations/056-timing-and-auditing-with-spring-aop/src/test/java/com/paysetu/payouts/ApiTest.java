package com.paysetu.payouts;

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
 * Shared setup: the app on a real PostgreSQL. Before each test: no payouts, no audit events, Chaiwala Traders (1)
 * has ₹50,000 and Desi Spices Co (2) ₹200.
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
    void freshBooks() {
        jdbc.sql("TRUNCATE payouts, audit_events RESTART IDENTITY").update();
        jdbc.sql("UPDATE merchants SET balance_paise = CASE id WHEN 1 THEN 5000000 ELSE 20000 END").update();
    }

    ResultActions payout(long merchant, long paise) throws Exception {
        return mvc.perform(post("/payouts").contentType(MediaType.APPLICATION_JSON).content(
                "{\"merchantId\":%d,\"amountPaise\":%d,\"ifsc\":\"HDFC0001234\",\"accountNumber\":\"50100123457890\"}".formatted(merchant, paise)));
    }

    long balance(long merchant) {
        return jdbc.sql("SELECT balance_paise FROM merchants WHERE id = ?").param(merchant).query(Long.class).single();
    }

    long auditEvents() {
        return jdbc.sql("SELECT count(*) FROM audit_events").query(Long.class).single();
    }
}
