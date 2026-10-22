package com.seatsure.holds;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: DELETE /holds/{id} gives the seats back at once (204); a confirmed hold cannot be released (409). */
class ReleaseHoldChallengeTest extends ApiTest {

    @Test
    void releasingFreesTheSeats() throws Exception {
        String id = holdId("meera", "F12", "F13");
        mvc.perform(delete("/holds/{id}", id)).andExpect(status().isNoContent());
        hold("arjun", "F12", "F13").andExpect(status().isCreated());
    }

    @Test
    void aConfirmedHoldStays() throws Exception {
        String id = holdId("meera", "F12");
        confirm(id);
        mvc.perform(delete("/holds/{id}", id)).andExpect(status().isConflict());
        mvc.perform(delete("/holds/{id}", "00000000-0000-0000-0000-000000000000")).andExpect(status().isNotFound());
    }
}
