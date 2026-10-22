package com.seatsure.holds;

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
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app on a real PostgreSQL, a clock the tests move, a lock timeout of half a second, and
 * before each test every seat free and the simulated payments fast.
 */
@SpringBootTest(properties = "seatsure.lock-timeout=500ms")
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final Instant START = Instant.parse("2026-10-30T12:00:00Z");
    static final JsonMapper JSON = JsonMapper.builder().build();

    static final class TestClock extends Clock {
        volatile Instant now = START;

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
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
    Payments payments;

    @BeforeEach
    void freeSeats() {
        CLOCK.now = START;
        payments.delay = Duration.ofMillis(10);
        payments.refunds.clear();
        jdbc.sql("TRUNCATE holds").update();
        jdbc.sql("UPDATE seats SET hold_id = NULL, held_until = NULL, booked_by = NULL").update();
    }

    void later(Duration d) {
        CLOCK.now = CLOCK.now.plus(d);
    }

    ResultActions holdRequest(String json) throws Exception {
        return mvc.perform(post("/shows/1/holds").contentType(MediaType.APPLICATION_JSON).content(json));
    }

    ResultActions hold(String customer, String... seats) throws Exception {
        return holdRequest("{\"customer\":\"%s\",\"seats\":[%s]}".formatted(customer, String.join(",", java.util.Arrays.stream(seats).map(s -> "\"" + s + "\"").toList())));
    }

    String holdId(String customer, String... seats) throws Exception {
        return body(hold(customer, seats)).get("id").asString();
    }

    ResultActions confirm(String holdId) throws Exception {
        return mvc.perform(post("/holds/{id}/confirm", holdId));
    }

    static JsonNode body(ResultActions r) throws Exception {
        return JSON.readTree(r.andReturn().getResponse().getContentAsString());
    }
}
