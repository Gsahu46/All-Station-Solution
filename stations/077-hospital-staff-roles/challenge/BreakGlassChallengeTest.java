package com.mediqo.wards;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasItem;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: break-glass. In an emergency a doctor may read the notes of a patient not in their care by sending
 * X-Emergency-Reason (10 to 200 characters). It works, and the audit marks it as an emergency with the reason.
 * Nurses cannot break the glass, and a reason that is too short does not count. Needs challenge 1's audit.
 */
class BreakGlassChallengeTest extends ApiTest {

    @Test
    void aDoctorCanBreakTheGlassAndItIsRecorded() throws Exception {
        mvc.perform(get("/patients/P-1001/notes").header("X-Emergency-Reason", "Collapsed in A&E, own doctor off duty")
                .with(httpBasic("dr.bose", "bose-demo-pass"))).andExpect(status().isOk());
        mvc.perform(get("/audit/notes-reads").with(httpBasic("admin.meena", "meena-demo-pass")))
                .andExpect(jsonPath("$[?(@.staff == 'dr.bose' && @.emergency == true)].reason", hasItem("Collapsed in A&E, own doctor off duty")));
    }

    @Test
    void nursesCannotAndAShortReasonDoesNotCount() throws Exception {
        mvc.perform(get("/patients/P-2001/notes").header("X-Emergency-Reason", "Collapsed in the corridor outside")
                .with(httpBasic("nurse.ritu", "ritu-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(get("/patients/P-1001/notes").header("X-Emergency-Reason", "urgent")
                .with(httpBasic("dr.bose", "bose-demo-pass"))).andExpect(status().isForbidden());
    }
}
