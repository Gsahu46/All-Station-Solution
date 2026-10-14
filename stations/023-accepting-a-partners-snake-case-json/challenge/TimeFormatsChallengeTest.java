package com.dakroute.partner;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the partner's v2 sends event_time as ISO 8601 with an offset ("2026-10-14T09:15:00+05:30"). Accept both
 * that and the old "2026-10-14 09:15:00" (India time), with a custom Jackson deserializer. ISO without an offset is
 * still refused: it does not say which zone.
 */
class TimeFormatsChallengeTest extends ApiTest {

    static String at(String eventTime) {
        return "{\"awb_number\":\"DKR100000001IN\",\"status_code\":\"ITR\",\"event_time\":\"" + eventTime + "\"}";
    }

    @Test
    void bothFormatsGiveTheSameInstant() throws Exception {
        update(at("2026-10-14 09:15:00")).andExpect(jsonPath("$.event.at").value("2026-10-14T03:45:00Z"));
        update(at("2026-10-14T09:15:00+05:30")).andExpect(jsonPath("$.event.at").value("2026-10-14T03:45:00Z"));
        update(at("2026-10-14T03:45:00Z")).andExpect(jsonPath("$.event.at").value("2026-10-14T03:45:00Z"));
    }

    @Test
    void aTimeWithoutAZoneInIsoFormIsStillRefused() throws Exception {
        update(at("2026-10-14T09:15:00")).andExpect(status().isBadRequest());
        update(at("yesterday")).andExpect(status().isBadRequest());
    }
}
