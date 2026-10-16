package com.kartwala.prices;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app on a real PostgreSQL, "now" fixed at 16 October 2026, 11:30 in India, and the demo
 * schedule restored before each test: product 2 has a Diwali sale from midnight 8 November to midnight 11 November.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final Instant NOW = Instant.parse("2026-10-16T06:00:00Z");

    @TestBean
    Clock clock;

    static Clock clock() {
        return Clock.fixed(NOW, ZoneOffset.UTC);
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void demoSchedule() {
        jdbc.sql("DELETE FROM prices").update();
        jdbc.sql("""
                INSERT INTO prices (product_id, price_paise, valid_from, valid_to) VALUES
                    (1, 49900, '2026-01-01 00:00+05:30', NULL),
                    (2, 19900, '2026-01-01 00:00+05:30', '2026-11-08 00:00+05:30'),
                    (2, 14900, '2026-11-08 00:00+05:30', '2026-11-11 00:00+05:30'),
                    (2, 19900, '2026-11-11 00:00+05:30', NULL),
                    (3, 89900, '2026-01-01 00:00+05:30', '2026-06-01 00:00+05:30'),
                    (3, 99900, '2026-06-01 00:00+05:30', NULL)""").update();
    }

    ResultActions priceAt(long product, String at) throws Exception {
        return mvc.perform(get("/products/{id}/price", product).param("at", at));
    }

    ResultActions setPrice(long product, int paise, String from, String to) throws Exception {
        String body = "{\"pricePaise\":%d,\"from\":\"%s\"%s}".formatted(paise, from, to == null ? "" : ",\"to\":\"" + to + "\"");
        return mvc.perform(post("/products/{id}/prices", product).contentType(MediaType.APPLICATION_JSON).content(body));
    }
}
