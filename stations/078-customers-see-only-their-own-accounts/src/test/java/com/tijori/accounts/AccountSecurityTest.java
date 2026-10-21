package com.tijori.accounts;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class AccountSecurityTest extends ApiTest {

    @Test
    void noOrWrongCredentialsAre401() throws Exception {
        mvc.perform(get("/accounts/1001")).andExpect(status().isUnauthorized()).andExpect(header().string("WWW-Authenticate", "Basic realm=\"tijori\""));
        mvc.perform(get("/accounts/1001").with(httpBasic("zoya@example.com", "guess"))).andExpect(status().isUnauthorized());
        mvc.perform(get("/accounts/1001").with(httpBasic("nobody@example.com", "guess"))).andExpect(status().isUnauthorized());
    }

    @Test
    void aBalanceOnlyHolderGets403ForStatementsAndAStrangerGets404() throws Exception {
        account("ravi", 1004).andExpect(status().isOk()).andExpect(jsonPath("$.access").value("balance_only"));
        statement("ravi", 1004, "2026-09").andExpect(status().isForbidden()).andExpect(jsonPath("$.detail").value("This sign-in may see the balance only"));
        statement("ravi", 1001, "2026-09").andExpect(status().isNotFound());   // not a holder: the account may as well not exist
    }

    @Test
    void removingAJointHolderTakesEffectOnTheNextRequest() throws Exception {
        account("dev", 1003).andExpect(status().isOk());
        jdbc.sql("DELETE FROM account_holders WHERE account_id = 1003 AND customer_id = (SELECT id FROM customers WHERE email = 'dev@example.com')").update();
        try {
            account("dev", 1003).andExpect(status().isNotFound());   // nothing cached on the account: the query decides each time
        } finally {
            jdbc.sql("INSERT INTO account_holders (account_id, customer_id, access) SELECT 1003, id, 'full' FROM customers WHERE email = 'dev@example.com'").update();
        }
    }

    @Test
    void oddIdsAndMonthsAre400Or404NeverAnError() throws Exception {
        for (String id : new String[]{"1001 OR 1=1", "1001;DROP TABLE accounts", "-1001", "99999999999999999999", "1001.0", "%31%30%30%32"}) {
            int s = account("zoya", id).andReturn().getResponse().getStatus();
            assertThat(s).as(id).isIn(400, 404);
        }
        statement("zoya", 1001, "2026-09' OR '1'='1").andExpect(status().isBadRequest());
    }

    @Test
    void writesAndOtherPathsAreRefused() throws Exception {
        mvc.perform(post("/accounts/1001").with(httpBasic("zoya@example.com", "zoya-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(delete("/accounts/1001").with(httpBasic("zoya@example.com", "zoya-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(get("/customers").with(httpBasic("zoya@example.com", "zoya-demo-pass"))).andExpect(status().isForbidden());
    }
}
