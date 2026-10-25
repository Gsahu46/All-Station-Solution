package com.taskloom.crm;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class LeadSecurityTest extends ApiTest {

    @Test
    void noSignInIs401AndAViewerCannotCreate() throws Exception {
        mvc.perform(get("/leads")).andExpect(status().isUnauthorized());
        mvc.perform(get("/leads").with(httpBasic("ananya", "wrong"))).andExpect(status().isUnauthorized());
        create("kabir", "{\"name\":\"X\",\"email\":\"x@example.com\"}").andExpect(status().isForbidden());
        list("kabir", "").andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(2));
    }

    @Test
    void anotherTenantsLeadIsNotFoundByIdOrBySearch() throws Exception {
        long brightpathLead = jdbc.sql("SELECT id FROM leads WHERE tenant_id = 'brightpath' AND email = 'sunil.rao@example.org'").query(Long.class).single();
        mvc.perform(get("/leads/{id}", brightpathLead).with(httpBasic("ananya", "ananya-demo-pass"))).andExpect(status().isNotFound());
        list("ananya", "?q=sunil").andExpect(jsonPath("$.length()").value(0));
        list("farhan", "?q=green").andExpect(jsonPath("$.length()").value(0));
    }

    @Test
    void searchTextIsTextNotSqlOrAPattern() throws Exception {
        searchFor("ananya", "%").andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(0));   // a literal %, not "anything"
        searchFor("ananya", "_").andExpect(jsonPath("$.length()").value(0));
        searchFor("ananya", "' OR '1'='1").andExpect(jsonPath("$.length()").value(0));
        searchFor("ananya", "x' OR tenant_id <> 'zestful").andExpect(jsonPath("$.length()").value(0));
        searchFor("ananya", "a").andExpect(jsonPath("$.length()").value(2));   // and ordinary text still finds
    }
}
