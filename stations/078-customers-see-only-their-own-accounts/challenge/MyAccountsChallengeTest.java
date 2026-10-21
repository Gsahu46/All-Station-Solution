package com.tijori.accounts;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: GET /accounts lists the signed-in customer's own accounts (id, name, access), by account number. */
class MyAccountsChallengeTest extends ApiTest {

    @Test
    void eachCustomerSeesOnlyTheirOwnList() throws Exception {
        mvc.perform(get("/accounts").with(httpBasic("zoya@example.com", "zoya-demo-pass"))).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].id", contains(1001, 1003)));
        mvc.perform(get("/accounts").with(httpBasic("ravi@example.com", "ravi-demo-pass")))
                .andExpect(jsonPath("$[*].id", contains(1004))).andExpect(jsonPath("$[0].access").value("balance_only"));
        mvc.perform(get("/accounts")).andExpect(status().isUnauthorized());
    }
}
