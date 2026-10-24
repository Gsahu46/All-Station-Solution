package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: the customer is told why a refund was refused, so a rejection needs a note. */
class RejectionNoteChallengeTest extends ApiTest {

    @Test
    void aRejectionWithoutANoteIs400AndTheNoteIsKept() throws Exception {
        long id = idOf(refund(PHONE, 1_000_000, "asha"));
        send(id, "{\"decision\":\"REJECT\"}").andExpect(status().isBadRequest());
        send(id, "{\"decision\":\"REJECT\",\"note\":\" \"}").andExpect(status().isBadRequest());
        send(id, "{\"decision\":\"REJECT\",\"note\":\"The phone was returned without its box.\"}")
                .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("REJECTED"))
                .andExpect(jsonPath("$.decisionNote").value("The phone was returned without its box."));
    }

    @Test
    void anApprovalNeedsNoNote() throws Exception {
        long id = idOf(refund(PHONE, 1_000_000, "asha"));
        send(id, "{\"decision\":\"APPROVE\"}").andExpect(status().isOk()).andExpect(jsonPath("$.decisionNote").isEmpty());
    }

    private org.springframework.test.web.servlet.ResultActions send(long id, String json) throws Exception {
        return mvc.perform(post("/refunds/{id}/approvals", id).with(httpBasic("raj", "raj-demo-pass"))
                .contentType(MediaType.APPLICATION_JSON).content(json));
    }
}
