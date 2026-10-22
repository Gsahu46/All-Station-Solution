package com.paysetu.payments;

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

/** Shared setup: the whole app on a real PostgreSQL, both simulated providers healthy and empty, no payments. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    AlphaApi alpha;
    @Autowired
    BetaApi beta;

    @BeforeEach
    void clean() {
        alpha.reset();
        beta.reset();
        jdbc.sql("TRUNCATE payments, refunds RESTART IDENTITY").update();
    }

    ResultActions pay(String json) throws Exception {
        return mvc.perform(post("/payments").contentType(MediaType.APPLICATION_JSON).content(json));
    }

    ResultActions pay(String orderId, long amountPaise) throws Exception {
        return pay("{\"orderId\":\"" + orderId + "\",\"amountPaise\":" + amountPaise + "}");
    }

    ResultActions refund(long paymentId, long amountPaise) throws Exception {
        return mvc.perform(post("/payments/{id}/refunds", paymentId).contentType(MediaType.APPLICATION_JSON).content("{\"amountPaise\":" + amountPaise + "}"));
    }

    String column(String sql) {
        return jdbc.sql(sql).query(String.class).single();
    }
}
