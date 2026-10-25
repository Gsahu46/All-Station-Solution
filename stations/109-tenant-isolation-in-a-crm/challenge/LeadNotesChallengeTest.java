package com.taskloom.crm;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: notes on a lead, in a new table. The note's tenant must be its lead's tenant, in the database: a
 * foreign key on (lead_id, tenant_id), and the same row-level policy as leads.
 */
class LeadNotesChallengeTest extends ApiTest {

    @BeforeEach
    void noNotes() {
        jdbc.sql("DELETE FROM lead_notes").update();
    }

    long id(String tenant, String email) {
        return jdbc.sql("SELECT id FROM leads WHERE tenant_id = ? AND email = ?").params(tenant, email).query(Long.class).single();
    }

    @Test
    void aNoteGoesOnYourOwnLeadOnly() throws Exception {
        mvc.perform(post("/leads/{id}/notes", id("zestful", "rahul@spicehub.example")).with(httpBasic("ananya", "ananya-demo-pass"))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"text\":\"Wants a tasting for 40 people in November.\"}"))
                .andExpect(status().isCreated()).andExpect(jsonPath("$.author").value("ananya"));
        mvc.perform(post("/leads/{id}/notes", id("brightpath", "rahul@spicehub.example")).with(httpBasic("ananya", "ananya-demo-pass"))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"text\":\"Hello\"}"))
                .andExpect(status().isNotFound());
    }

    @Test
    void theDatabaseRefusesANoteWhoseTenantIsNotItsLeads() {
        long theirs = id("brightpath", "sunil.rao@example.org");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO lead_notes (tenant_id, lead_id, author, text) VALUES ('zestful', ?, 'ananya', 'x')")
                .param(theirs).update()).hasMessageContaining("lead_notes_lead_of_same_tenant");
    }
}
