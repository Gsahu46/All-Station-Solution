package com.paysetu.payouts;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /payouts/{id}/cancellation cancels a REQUESTED payout and returns the money to the balance, and
 * is audited as PAYOUT_CANCELLED (subject: the payout id) without a line of audit code. Twice: 409. Unknown: 404.
 */
class CancelPayoutChallengeTest extends ApiTest {

    @Test
    void cancellingIsAuditedByTheAnnotationAlone() throws Exception {
        payout(1, 1_000_000);
        mvc.perform(post("/payouts/1/cancellation")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("CANCELLED"));
        assertThat(balance(1)).isEqualTo(5_000_000);
        mvc.perform(post("/payouts/1/cancellation")).andExpect(status().isConflict());
        mvc.perform(post("/payouts/99/cancellation")).andExpect(status().isNotFound());
        mvc.perform(get("/audit-events").param("action", "PAYOUT_CANCELLED")).andExpect(content().json("""
                [{"outcome":"FAILURE","subject":"99"},{"outcome":"FAILURE","subject":"1"},{"outcome":"SUCCESS","subject":"1"}]"""));
    }
}
