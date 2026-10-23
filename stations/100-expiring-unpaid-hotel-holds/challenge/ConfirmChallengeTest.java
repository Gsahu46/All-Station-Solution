package com.ghoomo.holds;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /holds/{id}/confirmation, called when the guest has paid (simulated: a status changes, no money
 * moves). A confirmed hold keeps its room and never expires. Too late (expired, or past its time): 409.
 */
class ConfirmChallengeTest extends ApiTest {

    @Test
    void aPaidHoldKeepsItsRoom() throws Exception {
        hold("pays-in-time1", 2, "2026-12-25", "asha@example.com").andExpect(status().isCreated());
        CLOCK.advance(Duration.ofMinutes(10));
        mvc.perform(post("/holds/1/confirmation")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("CONFIRMED"));
        mvc.perform(post("/holds/1/confirmation")).andExpect(status().isOk());   // a retry of the payment callback: no harm
        CLOCK.advance(Duration.ofHours(1));
        assertThat(holds.expireDue()).isZero();
        assertThat(held(2, "2026-12-25")).isEqualTo(1);
    }

    @Test
    void tooLateIs409() throws Exception {
        hold("pays-late-001", 1, "2026-12-25", "ravi@example.com").andExpect(status().isCreated());
        CLOCK.advance(Duration.ofMinutes(16));   // past its time, not swept yet
        mvc.perform(post("/holds/1/confirmation")).andExpect(status().isConflict());
        holds.expireDue();
        mvc.perform(post("/holds/1/confirmation")).andExpect(status().isConflict());
        mvc.perform(post("/holds/99/confirmation")).andExpect(status().isNotFound());
    }
}
