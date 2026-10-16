package com.taskloom.webinars;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: "repeat": "WEEKLY" — same weekday, same wall-clock time for the host, every week. A New York series
 * across 1 Nov 2026 (the US leaves daylight saving) stays at 10:00 for the host and moves by an hour in India.
 */
class WeeklyChallengeTest extends ApiTest {

    @Test
    void weeklyKeepsTheHostsWallClock() throws Exception {
        String url = created(webinar("2026-10-27T10:00", "America/New_York", ",\"repeat\":\"WEEKLY\",\"sessions\":2"));
        mvc.perform(get(url).param("viewerZone", "Asia/Kolkata")).andExpect(status().isOk())
                .andExpect(jsonPath("$.sessions[*].hostTime", contains("2026-10-27T10:00:00-04:00", "2026-11-03T10:00:00-05:00")))
                .andExpect(jsonPath("$.sessions[*].viewerTime", contains("2026-10-27T19:30:00+05:30", "2026-11-03T20:30:00+05:30")));
    }
}
