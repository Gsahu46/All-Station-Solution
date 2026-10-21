package com.taskloom.sharing;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /docs/{id}/shares/{subject} (subject like user:kabir or team:design) removes that subject's
 * viewer and editor tuples on the document (204). Editors and owners only; the owner tuple is never removed this way.
 */
class UnshareChallengeTest extends ApiTest {

    @Test
    void anOwnerTakesAShareBack() throws Exception {
        share("ravi", "d-roadmap", "user:kabir", "viewer").andExpect(status().isCreated());
        mvc.perform(delete("/docs/d-roadmap/shares/user:kabir").with(httpBasic("ravi", "ravi-demo-pass"))).andExpect(status().isNoContent());
        open("kabir", "d-roadmap").andExpect(status().isNotFound());
    }

    @Test
    void viewersCannotAndTheOwnerStays() throws Exception {
        mvc.perform(delete("/docs/d-guidelines/shares/team:design").with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(delete("/docs/d-roadmap/shares/user:ravi").with(httpBasic("meera", "meera-demo-pass"))).andExpect(status().isNoContent());
        open("ravi", "d-roadmap").andExpect(status().isOk());
    }
}
