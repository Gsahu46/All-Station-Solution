package com.seatsure.sales;

import io.micrometer.core.instrument.MeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static com.seatsure.sales.TestGateway.GATEWAY;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app on a real PostgreSQL with a small pool (4 connections, 1 s to get one) and a test
 * gateway whose answers have a 1 s limit, so a full pool and a slow gateway are quick to reach. Seats and orders are
 * reset before each test.
 */
@SpringBootTest(properties = {"spring.datasource.hikari.maximum-pool-size=4", "spring.datasource.hikari.connection-timeout=1000",
        "seatsure.payments.read-timeout=1s"})
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @DynamicPropertySource
    static void gateway(DynamicPropertyRegistry registry) {
        registry.add("seatsure.payments.url", GATEWAY::url);
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    MeterRegistry metrics;

    @BeforeEach
    void freshSale() {
        jdbc.sql("TRUNCATE orders RESTART IDENTITY").update();
        jdbc.sql("UPDATE sales SET sold = 0").update();
        GATEWAY.reset();
    }

    ResultActions order(long saleId, String buyer, int seats) throws Exception {
        return mvc.perform(post("/sales/{id}/orders", saleId).contentType(MediaType.APPLICATION_JSON)
                .content("{\"buyer\":\"" + buyer + "\",\"seats\":" + seats + "}"));
    }

    int sold(long saleId) {
        return jdbc.sql("SELECT sold FROM sales WHERE id = ?").param(saleId).query(Integer.class).single();
    }

    /** Requests that gave up waiting for a connection, as Hikari counts them. */
    double poolTimeouts() {
        var c = metrics.find("hikaricp.connections.timeout").counter();
        return c == null ? 0 : c.count();
    }
}
