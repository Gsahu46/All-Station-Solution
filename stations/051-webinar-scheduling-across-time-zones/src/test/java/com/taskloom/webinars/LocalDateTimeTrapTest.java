package com.taskloom.webinars;

import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** The first test written for this station: both bugs from the support tickets, then the same webinars through the fixed API. */
class LocalDateTimeTrapTest extends ApiTest {

    @Test
    void aLocalDateTimeShowsTenOClockToEveryone() throws Exception {
        var old = new OldWebinarStore.OldWebinar("Planning your first sprint", LocalDateTime.parse("2026-11-05T10:00"));
        assertThat(old.showTo("Europe/London")).isEqualTo(LocalDateTime.parse("2026-11-05T10:00"));   // 10:00 in London: wrong by 5h30

        String url = created(webinar("2026-11-05T10:00", "Asia/Kolkata", ""));
        mvc.perform(get(url).param("viewerZone", "Europe/London"))
                .andExpect(jsonPath("$.sessions[0].startsAt").value("2026-11-05T04:30:00Z"))
                .andExpect(jsonPath("$.sessions[0].hostTime").value("2026-11-05T10:00:00+05:30"))
                .andExpect(jsonPath("$.sessions[0].viewerTime").value("2026-11-05T04:30:00Z"));
    }

    @Test
    void repeatingInUtcMovesANewYorkSessionWhenDaylightSavingEnds() throws Exception {
        // 10:00 in New York on 20 Oct is 14:00 UTC. The US leaves daylight saving on 1 Nov 2026.
        var old = OldWebinarStore.monthlyInUtc(Instant.parse("2026-10-20T14:00:00Z"), 2);
        assertThat(old.get(1).atZone(ZoneId.of("America/New_York")).toLocalTime()).hasToString("09:00");   // the host's 10:00 became 09:00

        String url = created(webinar("2026-10-20T10:00", "America/New_York", ",\"repeat\":\"MONTHLY\",\"sessions\":2"));
        mvc.perform(get(url).param("viewerZone", "Asia/Kolkata"))
                .andExpect(jsonPath("$.sessions[1].hostTime").value("2026-11-20T10:00:00-05:00"))     // still 10:00 for the host
                .andExpect(jsonPath("$.sessions[0].viewerTime").value("2026-10-20T19:30:00+05:30"))
                .andExpect(jsonPath("$.sessions[1].viewerTime").value("2026-11-20T20:30:00+05:30"));  // an hour later in India, correctly
    }
}
