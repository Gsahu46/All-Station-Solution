package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.concurrent.atomic.AtomicReference;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: kitchens tap READY_FOR_PICKUP by mistake. Allow going back to PREPARING within 2 minutes of becoming
 * ready, and refuse it (409) after that. The table is unchanged: this is a rule about time, on top of it.
 */
@Import(UndoReadyChallengeTest.MovableClock.class)
class UndoReadyChallengeTest extends ApiTest {

    @TestConfiguration
    static class MovableClock {
        static final AtomicReference<Instant> NOW = new AtomicReference<>(Instant.parse("2026-10-14T12:00:00Z"));

        @Bean
        @Primary
        Clock movableClock() {
            return new Clock() {
                public Instant instant() {
                    return NOW.get();
                }

                public ZoneId getZone() {
                    return ZoneOffset.UTC;
                }

                public Clock withZone(ZoneId zone) {
                    return this;
                }
            };
        }
    }

    void advance(Duration d) {
        MovableClock.NOW.updateAndGet(t -> t.plus(d));
    }

    @Test
    void aMistakenReadyCanBeUndoneForTwoMinutes() throws Exception {
        change(1003, "READY_FOR_PICKUP").andExpect(status().isOk());
        advance(Duration.ofSeconds(90));
        change(1003, "PREPARING").andExpect(status().isOk()).andExpect(jsonPath("$.status").value("PREPARING"));
        change(1003, "READY_FOR_PICKUP").andExpect(status().isOk());
        advance(Duration.ofMinutes(3));
        change(1003, "PREPARING").andExpect(status().isConflict());
    }
}
