package com.kartwala.recent;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 2: views older than 30 days are not shown. Time is moved by a test clock, not waited for. */
@Import(ExpiryChallengeTest.Clocks.class)
class ExpiryChallengeTest extends ApiTest {

    static class MovableClock extends Clock {
        Instant now = Instant.parse("2026-10-01T10:00:00Z");

        @Override
        public Instant instant() {
            return now;
        }

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }
    }

    @TestConfiguration
    static class Clocks {
        @Bean
        @Primary
        MovableClock movableClock() {
            return new MovableClock();
        }
    }

    @Autowired
    MovableClock clock;

    @Test
    void aViewOlderThanThirtyDaysDisappears() throws Exception {
        view(7, 101);
        clock.now = clock.now.plus(Duration.ofDays(29));
        view(7, 102);
        mvc.perform(get("/users/7/recently-viewed")).andExpect(jsonPath("$.productIds", contains(102, 101)));
        clock.now = clock.now.plus(Duration.ofDays(2));    // 101 is now 31 days old
        mvc.perform(get("/users/7/recently-viewed")).andExpect(jsonPath("$.productIds", contains(102)));
    }

    @Test
    void viewingAgainRestartsTheThirtyDays() throws Exception {
        view(7, 201);
        clock.now = clock.now.plus(Duration.ofDays(25));
        view(7, 201);
        clock.now = clock.now.plus(Duration.ofDays(25));
        mvc.perform(get("/users/7/recently-viewed")).andExpect(jsonPath("$.productIds", contains(201)));
    }
}
