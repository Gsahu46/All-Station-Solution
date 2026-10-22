package com.paysetu.cards;

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
import tools.jackson.databind.json.JsonMapper;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app on a real PostgreSQL, a clock the tests move, the network simulation empty, the demo customers. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    /** Standard test card numbers: they pass the check digit and belong to nobody. */
    static final String VISA = "4111111111111111";
    static final String MASTERCARD = "5555555555554444";
    static final String RUPAY = "6521000000000015";
    static final long ASHA = 1;
    static final long ROHAN = 2;
    static final Instant NOW = Instant.parse("2026-10-30T06:30:00Z");

    static final class TestClock extends Clock {
        volatile Instant now = NOW;

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            TestClock outer = this;
            return new Clock() {
                public ZoneId getZone() {
                    return zone;
                }

                public Clock withZone(ZoneId z) {
                    return outer.withZone(z);
                }

                public Instant instant() {
                    return outer.now;
                }
            };
        }

        @Override
        public Instant instant() {
            return now;
        }
    }

    static final TestClock CLOCK = new TestClock();

    @TestBean
    Clock clock;

    static Clock clock() {
        return CLOCK;
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    SimNetwork network;

    @BeforeEach
    void clean() throws Exception {
        CLOCK.now = NOW;
        network.reset();
        jdbc.sql("TRUNCATE customers, saved_cards, payments RESTART IDENTITY").update();
        jdbc.sql(Files.readString(Path.of("src/main/resources/db/migration/V2__demo_customers.sql"))).update();
    }

    static String password(String user) {
        return user + "-demo-pass";
    }

    ResultActions save(String user, long customer, String json) throws Exception {
        return mvc.perform(post("/customers/{id}/saved-cards", customer).with(httpBasic(user, password(user))).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    ResultActions save(String user, long customer, String cardNumber, int month, int year) throws Exception {
        return save(user, customer, "{\"cardNumber\":\"%s\",\"expiryMonth\":%d,\"expiryYear\":%d,\"consent\":true}".formatted(cardNumber, month, year));
    }

    long savedCardId(String user, long customer, String cardNumber) throws Exception {
        String body = save(user, customer, cardNumber, 12, 2028).andReturn().getResponse().getContentAsString();
        return JsonMapper.builder().build().readTree(body).get("id").asLong();
    }

    ResultActions list(String user, long customer) throws Exception {
        return mvc.perform(get("/customers/{id}/saved-cards", customer).with(httpBasic(user, password(user))));
    }

    ResultActions pay(String user, String orderId, long savedCardId, long amountPaise) throws Exception {
        return mvc.perform(post("/payments").with(httpBasic(user, password(user))).contentType(MediaType.APPLICATION_JSON)
                .content("{\"orderId\":\"%s\",\"savedCardId\":%d,\"amountPaise\":%d}".formatted(orderId, savedCardId, amountPaise)));
    }
}
