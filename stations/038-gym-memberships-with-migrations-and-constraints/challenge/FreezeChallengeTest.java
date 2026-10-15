package com.fitnest.members;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /memberships/{id}/freeze {"days": n} pauses a membership: its end moves n days later. At most 30
 * frozen days per membership (a Java check for the message, and memberships_freeze_limit in a new migration). A freeze
 * that would run into the member's next membership is refused by the overlap rule that already exists: 409.
 */
class FreezeChallengeTest extends ApiTest {

    ResultActions freeze(long membershipId, int days) throws Exception {
        return mvc.perform(post("/memberships/{id}/freeze", membershipId).contentType(MediaType.APPLICATION_JSON).content("{\"days\":" + days + "}"));
    }

    @Test
    void aFreezeMovesTheEndUpToThirtyDaysInAll() throws Exception {
        join("Asha", "9876543210");
        buy(1, "MONTHLY", "2026-11-01");
        freeze(1, 10).andExpect(status().isOk()).andExpect(jsonPath("$.endsOn").value("2026-12-10")).andExpect(jsonPath("$.frozenDays").value(10));
        freeze(1, 25).andExpect(status().isUnprocessableContent());
        freeze(1, 20).andExpect(status().isOk()).andExpect(jsonPath("$.endsOn").value("2026-12-30"));
        assertThatThrownBy(() -> jdbc.sql("UPDATE memberships SET frozen_days = 31 WHERE id = 1").update())
                .hasMessageContaining("memberships_freeze_limit");
    }

    @Test
    void aFreezeCannotRunIntoTheNextMembership() throws Exception {
        join("Asha", "9876543210");
        buy(1, "MONTHLY", "2026-11-01");
        buy(1, "MONTHLY", "2026-12-01");
        freeze(1, 1).andExpect(status().isConflict());
        freeze(99, 1).andExpect(status().isNotFound());
    }
}
