package com.chaupal.accounts;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class AccountContractTest extends ApiTest {

    static final JsonMapper JSON = JsonMapper.builder().build();

    @Test
    void anExportIsAJobAndHoldsThePersonsOwnDataOnly() throws Exception {
        requestExport("imran").andExpect(status().isAccepted()).andExpect(header().string("Location", "/me/data-exports/1"))
                .andExpect(jsonPath("$.status").value("PENDING"));
        accounts.runJobs();
        as("imran", get("/me/data-exports/1")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("READY"));

        var file = exportFile("imran", 1).andExpect(status().isOk())
                .andExpect(header().string("Content-Disposition", "attachment; filename=\"chaupal-data-1.json\"")).andReturn().getResponse();
        JsonNode data = JSON.readTree(file.getContentAsString());
        assertThat(data.path("account").get(0).path("phone").asString()).isEqualTo("+919811122233");
        assertThat(data.path("posts")).hasSize(1);
        assertThat(data.path("comments")).hasSize(1);
        assertThat(data.path("invoices")).hasSize(1);
        assertThat(data.path("contactsYouUploaded").get(0).path("contact_name").asString()).isEqualTo("Zoya");
        assertThat(file.getContentAsString()).as("Zoya's address book is hers, even where it names Imran").doesNotContain("Imran cricket");
    }

    @Test
    void deletingClosesTheAccountAtOnceAndBooksTheErasureWithin90Days() throws Exception {
        var answer = deleteMe("imran").andExpect(status().isAccepted()).andExpect(jsonPath("$.status").value("DELETION_REQUESTED"));
        Instant dueBy = Instant.parse(JSON.readTree(answer.andReturn().getResponse().getContentAsString()).path("dueBy").asString());
        assertThat(dueBy).isBetween(Instant.now().plus(Duration.ofDays(89)), Instant.now().plus(Duration.ofDays(91)));
        deleteMe("imran").andExpect(status().isUnauthorized());
        eraseNow(1);
        assertThat(jdbc.sql("SELECT status FROM users WHERE id = 1").query(String.class).single()).isEqualTo("DELETED");
        assertThat(jdbc.sql("SELECT count(*) FROM login_events WHERE user_id = 1").query(Integer.class).single())
                .as("the sign-in from 2 days ago is kept for security; the one from 200 days ago is gone").isEqualTo(1);
    }

    @Test
    void anUnknownExportIs404AndABadIdIs400() throws Exception {
        as("zoya", get("/me/data-exports/{id}", 99)).andExpect(status().isNotFound());
        exportFile("zoya", 99).andExpect(status().isNotFound());
        as("zoya", get("/me/data-exports/{id}", "1 OR 1=1")).andExpect(status().isBadRequest());
    }
}
