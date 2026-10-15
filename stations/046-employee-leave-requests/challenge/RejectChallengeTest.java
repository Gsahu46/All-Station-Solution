package com.teamdesk.leave;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /leave-requests/{id}/rejection with {"note": "..."} (1 to 200 characters) turns a PENDING request
 * into REJECTED and leaves the balance alone. A request that is already decided is 409; an unknown one is 404.
 */
class RejectChallengeTest extends ApiTest {

    org.springframework.test.web.servlet.ResultActions reject(long id) throws Exception {
        return mvc.perform(post("/leave-requests/{id}/rejection", id).contentType(MediaType.APPLICATION_JSON)
                .content("{\"note\":\"Quarter-end release that week\"}"));
    }

    @Test
    void aRejectionKeepsTheBalance() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        reject(id).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("REJECTED"));
        mvc.perform(get("/employees/1/leave-balance")).andExpect(jsonPath("$.balanceDays").value(12));
        approve(id).andExpect(status().isConflict());
    }

    @Test
    void anApprovedOrUnknownRequestCannotBeRejected() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        approve(id).andExpect(status().isOk());
        reject(id).andExpect(status().isConflict());
        reject(999).andExpect(status().isNotFound());
        mvc.perform(post("/leave-requests/{id}/rejection", id).contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
    }
}
