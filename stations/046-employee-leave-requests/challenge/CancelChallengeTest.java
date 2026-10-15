package com.teamdesk.leave;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /leave-requests/{id}/cancellation cancels APPROVED leave: status CANCELLED and the days go back
 * to the balance, both in one transaction. Anything not APPROVED is 409. The database must accept the new status.
 */
class CancelChallengeTest extends ApiTest {

    @Test
    void cancellingApprovedLeaveGivesTheDaysBack() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        approve(id).andExpect(status().isOk());
        mvc.perform(post("/leave-requests/{id}/cancellation", id)).andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CANCELLED")).andExpect(jsonPath("$.balanceDays").value(12));
        mvc.perform(get("/employees/1/leave-balance")).andExpect(jsonPath("$.balanceDays").value(12));
        assertThat(statusInTheDatabase(id)).isEqualTo("CANCELLED");
        mvc.perform(post("/leave-requests/{id}/cancellation", id)).andExpect(status().isConflict());
    }

    @Test
    void onlyApprovedLeaveCanBeCancelled() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        mvc.perform(post("/leave-requests/{id}/cancellation", id)).andExpect(status().isConflict());
        mvc.perform(post("/leave-requests/{id}/cancellation", 999)).andExpect(status().isNotFound());
    }
}
