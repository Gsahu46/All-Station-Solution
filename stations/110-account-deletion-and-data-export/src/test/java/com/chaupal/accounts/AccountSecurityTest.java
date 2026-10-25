package com.chaupal.accounts;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class AccountSecurityTest extends ApiTest {

    @Test
    void noSignInIs401AndASupportAccountHasNoMe() throws Exception {
        mvc.perform(delete("/me")).andExpect(status().isUnauthorized());
        mvc.perform(get("/me/data-exports/1").with(org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic("imran", "wrong")))
                .andExpect(status().isUnauthorized());
        deleteMe("support").andExpect(status().isForbidden());
    }

    @Test
    void onePersonCannotReadAnothersExport() throws Exception {
        requestExport("imran").andExpect(status().isAccepted());
        accounts.runJobs();
        exportFile("imran", 1).andExpect(status().isOk());
        as("zoya", get("/me/data-exports/{id}", 1)).andExpect(status().isNotFound());
        exportFile("zoya", 1).andExpect(status().isNotFound());
    }

    @Test
    void anExportNotYetReadyIs409() throws Exception {
        requestExport("zoya").andExpect(status().isAccepted());
        exportFile("zoya", 1).andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("The export is not ready yet."));
    }
}
