package com.tijori.wallets;

import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The day is India's: it starts at 00:00 IST, which is 18:30 UTC the evening before. */
class IstDayBoundaryTest extends ApiTest {

    @Test
    void theLimitResetsAtMidnightInIndia() throws Exception {
        CLOCK.now = Instant.parse("2026-10-30T18:29:59Z");   // 23:59:59 IST on 30 Oct
        topUp(ANANYA, 900000).andExpect(status().isCreated());
        topUp(ANANYA, 200000).andExpect(status().isConflict());
        CLOCK.now = Instant.parse("2026-10-30T18:30:00Z");   // 00:00 IST on 31 Oct: a new day
        topUp(ANANYA, 900000).andExpect(status().isCreated()).andExpect(jsonPath("$.toppedUpTodayPaise").value(900000));
    }

    @Test
    void earlyMorningInIndiaIsTheSameDayAsTheEveningBeforeInUtc() throws Exception {
        CLOCK.now = Instant.parse("2026-10-30T19:00:00Z");   // 00:30 IST on 31 Oct, still 30 Oct in UTC
        topUp(ANANYA, 600000).andExpect(status().isCreated());
        CLOCK.now = Instant.parse("2026-10-31T01:00:00Z");   // 06:30 IST on 31 Oct, 31 Oct in UTC too
        topUp(ANANYA, 600000).andExpect(status().isConflict()).andExpect(jsonPath("$.remainingTodayPaise").value(400000));
    }
}
