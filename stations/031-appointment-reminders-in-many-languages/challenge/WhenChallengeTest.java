package com.mediqo.reminders;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: add a "when" field to the reminder: "today", "tomorrow" or "in 5 days" (in Hindi: आज, कल, 5 दिन में),
 * from one message with a choice format, not from if/else in Java. Days are counted in India's time zone, from a
 * Clock bean, so a test can set "now".
 */
@Import(WhenChallengeTest.TestClock.class)
class WhenChallengeTest extends ApiTest {

    /** A clock the test moves by hand. Starts at the Unix epoch, in UTC like a typical server. */
    static class SettableClock extends Clock {
        volatile Instant now = Instant.EPOCH;

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return Clock.fixed(now, zone);
        }

        @Override
        public Instant instant() {
            return now;
        }
    }

    @TestConfiguration
    static class TestClock {
        @Bean
        @Primary
        SettableClock settableClock() {
            return new SettableClock();
        }
    }

    @Autowired
    SettableClock clock;

    @Test
    void daysUntilTheAppointmentInBothLanguages() throws Exception {
        clock.now = Instant.parse("2026-10-15T06:00:00Z");   // Asha's appointment is on 20 October
        reminder(501, "en", null).andExpect(jsonPath("$.when").value("in 5 days"));
        reminder(501, "hi", null).andExpect(jsonPath("$.when").value("5 दिन में"));
        clock.now = Instant.parse("2026-10-19T06:00:00Z");
        reminder(501, "en", null).andExpect(jsonPath("$.when").value("tomorrow"));
        reminder(501, "hi", null).andExpect(jsonPath("$.when").value("कल"));
    }

    @Test
    void todayMeansTodayInIndiaNotOnTheServer() throws Exception {
        clock.now = Instant.parse("2026-10-19T20:00:00Z");   // still the 19th in UTC, already 01:30 on the 20th in India
        reminder(501, "en", null).andExpect(jsonPath("$.when").value("today"));
        reminder(501, "hi", null).andExpect(jsonPath("$.when").value("आज"));
    }
}
