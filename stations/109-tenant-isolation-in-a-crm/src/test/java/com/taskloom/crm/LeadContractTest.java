package com.taskloom.crm;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class LeadContractTest extends ApiTest {

    @Test
    void aTenantListsAndFiltersItsOwnLeads() throws Exception {
        list("ananya", "").andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(2));
        list("ananya", "?status=QUALIFIED").andExpect(jsonPath("$.length()").value(1)).andExpect(jsonPath("$[0].name").value("Rahul Mehta"));
        list("ananya", "?q=BOWL").andExpect(jsonPath("$.length()").value(1)).andExpect(jsonPath("$[0].company").value("Green Bowl Cafe"));
        list("farhan", "?q=sunrise").andExpect(jsonPath("$[0].email").value("sunil.rao@example.org"));
    }

    @Test
    void aLeadIsCreatedOnceAnEmailPerTenant() throws Exception {
        var created = create("ananya", "{\"name\":\" Divya Kapoor \",\"email\":\"Divya@MasalaBox.example\",\"company\":\"Masala Box\"}")
                .andExpect(status().isCreated()).andExpect(jsonPath("$.email").value("divya@masalabox.example"))
                .andExpect(jsonPath("$.name").value("Divya Kapoor")).andExpect(jsonPath("$.status").value("NEW"))
                .andExpect(jsonPath("$.owner").value("ananya"));
        long id = Long.parseLong(created.andReturn().getResponse().getContentAsString().replaceAll(".*\"id\":(\\d+).*", "$1"));
        created.andExpect(header().string("Location", "/leads/" + id));
        mvc.perform(get("/leads/{id}", id).with(httpBasic("kabir", "kabir-demo-pass"))).andExpect(status().isOk());

        create("ananya", "{\"name\":\"Divya K\",\"email\":\"divya@masalabox.example\"}").andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("Your company already has a lead with this email."));
        create("farhan", "{\"name\":\"Divya Kapoor\",\"email\":\"divya@masalabox.example\"}").andExpect(status().isCreated());
    }

    @Test
    void badInputIs400AndAnUnknownLeadIs404() throws Exception {
        create("ananya", "{\"name\":\"X\",\"email\":\"not-an-email\"}").andExpect(status().isBadRequest());
        create("ananya", "{\"name\":\"X\",\"email\":\"x@example.com\",\"status\":\"WON\"}").andExpect(status().isBadRequest());
        create("ananya", "{\"email\":\"x@example.com\"}").andExpect(status().isBadRequest());
        list("ananya", "?status=WON").andExpect(status().isBadRequest());
        list("ananya", "?q=" + "a".repeat(101)).andExpect(status().isBadRequest());
        mvc.perform(get("/leads/{id}", 99999).with(httpBasic("ananya", "ananya-demo-pass"))).andExpect(status().isNotFound());
    }
}
