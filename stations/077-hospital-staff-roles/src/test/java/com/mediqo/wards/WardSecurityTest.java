package com.mediqo.wards;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.AuthorityUtils;
import org.springframework.security.core.context.SecurityContextHolder;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class WardSecurityTest extends ApiTest {

    @Autowired
    WardController controller;

    @AfterEach
    void signOut() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void noOrWrongCredentialsAre401() throws Exception {
        mvc.perform(get("/patients/P-1001/notes")).andExpect(status().isUnauthorized()).andExpect(header().string("WWW-Authenticate", "Basic realm=\"mediqo\""));
        mvc.perform(get("/patients/P-1001/notes").with(httpBasic("dr.sharma", "guess"))).andExpect(status().isUnauthorized());
        mvc.perform(get("/patients/P-1001/notes").with(httpBasic("dr.nobody", "guess"))).andExpect(status().isUnauthorized());
    }

    @Test
    void aDoctorCannotReadOrPrescribeForAnotherDoctorsPatient() throws Exception {
        notes("dr.bose", "P-1001").andExpect(status().isForbidden()).andExpect(jsonPath("$.title").value("Not allowed"));
        prescribe("dr.bose", "P-1001", ASPIRIN).andExpect(status().isForbidden());
    }

    @Test
    void aNurseCannotReadNotesFromAnotherWard() throws Exception {
        notes("nurse.joseph", "P-1001").andExpect(status().isForbidden());
        notes("nurse.ritu", "P-2001").andExpect(status().isForbidden());
    }

    @Test
    void theCodeRefusesEvenIfARequestRuleIsMissing() {
        // Calling the controller directly skips the filter chain, as a new route or a forgotten rule would.
        SecurityContextHolder.getContext().setAuthentication(UsernamePasswordAuthenticationToken.authenticated("reception.anu", null,
                AuthorityUtils.createAuthorityList("ROLE_RECEPTIONIST", "appointments:read")));
        assertThatThrownBy(() -> controller.notes("P-1001")).isInstanceOf(AccessDeniedException.class);
        SecurityContextHolder.getContext().setAuthentication(UsernamePasswordAuthenticationToken.authenticated("dr.bose", null,
                AuthorityUtils.createAuthorityList("ROLE_DOCTOR", "notes:read")));
        assertThatThrownBy(() -> controller.notes("P-1001")).isInstanceOf(AccessDeniedException.class);   // right role, wrong patient
    }

    @Test
    void pathsWithoutARuleAreRefused() throws Exception {
        mvc.perform(get("/patients/P-1001/prescriptions").with(httpBasic("dr.sharma", "sharma-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(delete("/patients/P-1001/notes").with(httpBasic("dr.sharma", "sharma-demo-pass"))).andExpect(status().isForbidden());
    }

    @Test
    void oddPatientIdsAre403Or400NeverAnError() throws Exception {
        for (String id : new String[]{"..%2FP-1001", "P-1001' OR '1'='1", "P-1001;DROP", "a".repeat(2000), "p-1001"}) {
            int s = notes("dr.sharma", id).andReturn().getResponse().getStatus();
            org.assertj.core.api.Assertions.assertThat(s).as(id.length() > 40 ? id.substring(0, 40) : id).isIn(400, 403);
        }
    }
}
