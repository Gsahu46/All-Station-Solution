package com.tiffino.orders;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the app on a real PostgreSQL, no orders before each test. The sequence is never reset. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final String ORDER_NUMBER = "TF-\\d{7}-\\d";

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    OrderStore store;

    @BeforeEach
    void noOrders() {
        jdbc.sql("TRUNCATE orders RESTART IDENTITY").update();
    }

    ResultActions place(String json) throws Exception {
        return mvc.perform(post("/orders").contentType(MediaType.APPLICATION_JSON).content(json));
    }

    ResultActions lookUp(String number) throws Exception {
        return mvc.perform(get("/orders/by-number/{n}", number));
    }

    long orders() {
        return jdbc.sql("SELECT count(*) FROM orders").query(Long.class).single();
    }

    /** A correctly formed number with a valid check digit. */
    static String validNumber(long digits) {
        return "TF-" + digits + "-" + OrderNumbers.checkDigit(Long.toString(digits));
    }
}
