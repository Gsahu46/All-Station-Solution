package com.dakroute.partner;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: the partner retries when our answer is slow, so the same update can arrive twice. The same AWB, status
 * and event time is one event: the second copy is accepted, marked duplicate, and not stored again.
 */
class DuplicateUpdateChallengeTest extends ApiTest {

    static final String UPDATE = "{\"awb_number\":\"DKR100000002IN\",\"status_code\":\"PKD\",\"event_time\":\"2026-10-13 18:20:00\"}";

    @Test
    void theSameUpdateTwiceIsOneEvent() throws Exception {
        // other tests may have added events to this shipment already: count from the first answer
        int before = JsonPath.read(update(UPDATE).andExpect(status().isAccepted()).andExpect(jsonPath("$.duplicate").value(false))
                .andReturn().getResponse().getContentAsString(), "$.eventsForShipment");
        update(UPDATE).andExpect(status().isAccepted()).andExpect(jsonPath("$.duplicate").value(true))
                .andExpect(jsonPath("$.eventsForShipment").value(before));
        update(UPDATE.replace("18:20:00", "18:21:00")).andExpect(jsonPath("$.duplicate").value(false))
                .andExpect(jsonPath("$.eventsForShipment").value(before + 1));
    }
}
