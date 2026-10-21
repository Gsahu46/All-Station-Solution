package com.mediqo.wards;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasItem;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: every read of clinical notes is recorded (staff, patient). GET /audit/notes-reads lists them for the
 * privacy officer admin.meena (password "meena-demo-pass", permission audit:read) only; clinicians get 403.
 */
class NotesAuditChallengeTest extends ApiTest {

    @Test
    void thePrivacyOfficerSeesWhoReadWhichNotes() throws Exception {
        notes("dr.sharma", "P-1002").andExpect(status().isOk());
        mvc.perform(get("/audit/notes-reads").with(httpBasic("admin.meena", "meena-demo-pass"))).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].staff", hasItem("dr.sharma"))).andExpect(jsonPath("$[*].patientId", hasItem("P-1002")));
    }

    @Test
    void cliniciansCannotReadTheAudit() throws Exception {
        mvc.perform(get("/audit/notes-reads").with(httpBasic("dr.sharma", "sharma-demo-pass"))).andExpect(status().isForbidden());
    }
}
