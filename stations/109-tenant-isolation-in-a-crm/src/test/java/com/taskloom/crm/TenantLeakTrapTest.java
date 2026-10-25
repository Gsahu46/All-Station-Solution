package com.taskloom.crm;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Ananya works at Zestful Foods. Rahul Mehta is a lead of Zestful's and of Brightpath's. Written first. */
class TenantLeakTrapTest extends ApiTest {

    @Autowired
    TenantScope scope;

    /** The old repository: the tenant came in the request, and one lookup forgot it. Ran as the database owner. */
    void oldCreate(String tenantFromBody, String email) {
        jdbc.sql("INSERT INTO leads (tenant_id, name, email, status, owner) VALUES (?, 'Planted Lead', ?, 'NEW', 'ananya')")
                .params(tenantFromBody, email).update();
    }

    List<String> oldFindByEmail(String email) {
        return jdbc.sql("SELECT tenant_id || ':' || company FROM leads WHERE email = ? ORDER BY tenant_id").param(email).query(String.class).list();
    }

    @Test
    void theOldCodeTrustedTheBodysTenantAndForgotTheTenantInOneQuery() {
        oldCreate("brightpath", "planted@example.com");   // Ananya's request, a tenant she typed in
        assertThat(tenantOf("planted@example.com")).isEqualTo("brightpath");
        assertThat(oldFindByEmail("rahul@spicehub.example")).as("Ananya sees Brightpath's notes on the lead")
                .containsExactly("brightpath:Spice Hub", "zestful:Spice Hub");
    }

    @Test
    void theApiTakesTheTenantFromTheSignInAndTheDatabaseFiltersWhatACodeForgets() throws Exception {
        create("ananya", "{\"tenantId\":\"brightpath\",\"name\":\"Planted Lead\",\"email\":\"planted@example.com\"}")
                .andExpect(status().isCreated());
        assertThat(tenantOf("planted@example.com")).isEqualTo("zestful");

        list("ananya", "?q=rahul&tenant=brightpath").andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1)).andExpect(jsonPath("$[0].owner").value("ananya"));

        // The same forgetful query as before, but inside a tenant's transaction: the policy filters it.
        List<String> found = scope.run("zestful", () -> oldFindByEmail("rahul@spicehub.example"));
        assertThat(found).containsExactly("zestful:Spice Hub");
    }
}
