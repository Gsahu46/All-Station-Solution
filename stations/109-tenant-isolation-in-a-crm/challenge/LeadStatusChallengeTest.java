package com.taskloom.crm;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: PATCH /leads/{id} {status}: a salesperson moves their company's lead along; nobody else's. */
class LeadStatusChallengeTest extends ApiTest {

    long id(String tenant, String email) {
        return jdbc.sql("SELECT id FROM leads WHERE tenant_id = ? AND email = ?").params(tenant, email).query(Long.class).single();
    }

    @Test
    void aSalespersonChangesTheirOwnLeadsStatus() throws Exception {
        long lead = id("zestful", "leela@greenbowl.example");
        mvc.perform(patch("/leads/{id}", lead).with(httpBasic("ananya", "ananya-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"CONTACTED\"}")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("CONTACTED"));
        mvc.perform(patch("/leads/{id}", lead).with(httpBasic("ananya", "ananya-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"WON\"}")).andExpect(status().isBadRequest());
        mvc.perform(patch("/leads/{id}", lead).with(httpBasic("kabir", "kabir-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"LOST\"}")).andExpect(status().isForbidden());
        jdbc.sql("UPDATE leads SET status = 'NEW' WHERE id = ?").param(lead).update();
    }

    @Test
    void anotherTenantsLeadIsNotFoundAndUnchanged() throws Exception {
        long theirs = id("brightpath", "sunil.rao@example.org");
        mvc.perform(patch("/leads/{id}", theirs).with(httpBasic("ananya", "ananya-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"LOST\"}")).andExpect(status().isNotFound());
        assertThat(jdbc.sql("SELECT status FROM leads WHERE id = ?").param(theirs).query(String.class).single()).isEqualTo("CONTACTED");
    }
}
