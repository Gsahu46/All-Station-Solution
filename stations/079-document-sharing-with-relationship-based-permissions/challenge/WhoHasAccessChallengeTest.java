package com.taskloom.sharing;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /docs/{id}/access lists every user who can open the document, with their strongest access,
 * through folders and teams in teams (Zanzibar's "expand"), sorted by user. Editors and owners only.
 */
class WhoHasAccessChallengeTest extends ApiTest {

    @Test
    void everyoneWhoCanOpenTheGuidelines() throws Exception {
        mvc.perform(get("/docs/d-guidelines/access").with(httpBasic("ravi", "ravi-demo-pass"))).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].user", contains("asha", "neha", "ravi")))
                .andExpect(jsonPath("$[*].access", contains("viewer", "viewer", "owner")));
    }

    @Test
    void viewersCannotSeeTheList() throws Exception {
        mvc.perform(get("/docs/d-guidelines/access").with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(get("/docs/d-salaries/access").with(httpBasic("kabir", "kabir-demo-pass"))).andExpect(status().isNotFound());
    }
}
