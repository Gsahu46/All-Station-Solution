package com.tijori.transfers;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.util.List;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the app on a real PostgreSQL. Before each test: no transfers or events, Asha (1) ₹25,000, Ravi (2) ₹100. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void freshBank() {
        jdbc.sql("TRUNCATE transfers, audit_events RESTART IDENTITY").update();
        jdbc.sql("UPDATE accounts SET balance_paise = CASE id WHEN 1 THEN 2500000 ELSE 10000 END").update();
    }

    ResultActions transfer(long from, long to, long paise) throws Exception {
        return mvc.perform(post("/transfers").contentType(MediaType.APPLICATION_JSON)
                .content("{\"fromAccountId\":%d,\"toAccountId\":%d,\"amountPaise\":%d}".formatted(from, to, paise)));
    }

    /** Every event, oldest first, as "EVENT reason". */
    List<String> events() {
        return jdbc.sql("SELECT event || coalesce(' ' || reason, '') FROM audit_events ORDER BY id").query(String.class).list();
    }

    long balance(long account) {
        return jdbc.sql("SELECT balance_paise FROM accounts WHERE id = ?").param(account).query(Long.class).single();
    }
}
