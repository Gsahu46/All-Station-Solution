package com.kartwala.prices;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.AuthorityUtils;
import org.springframework.security.core.context.SecurityContextHolder;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PriceSecurityTest extends ApiTest {

    @Autowired
    Prices prices;

    @AfterEach
    void signOut() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void noOrWrongCredentialsAre401() throws Exception {
        mvc.perform(get("/products/1/history")).andExpect(status().isUnauthorized()).andExpect(header().string("WWW-Authenticate", "Basic realm=\"kartwala\""));
        mvc.perform(get("/products/1/history").with(httpBasic("neha.store", "guess"))).andExpect(status().isUnauthorized());
    }

    @Test
    void anotherSellersProductIs404AndUnchanged() throws Exception {
        setPrice("arun.mart", 1, 100).andExpect(status().isNotFound());
        history("arun.mart", 1).andExpect(status().isNotFound());
        history("priya.ops", 1).andExpect(jsonPath("$[0].pricePaise").value(5499900));
    }

    @Test
    void supportReadsAnyHistoryButCannotChangeAPrice() throws Exception {
        history("sam.help", 3).andExpect(status().isOk());
        setPrice("sam.help", 3, 100).andExpect(status().isForbidden());
    }

    @Test
    void aHeaderNamingSomeoneElseIsIgnored() throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put("/products/1/price").header("X-Changed-By", "priya.ops")
                .with(httpBasic("neha.store", "neha-demo-pass")).contentType(org.springframework.http.MediaType.APPLICATION_JSON).content("{\"pricePaise\":549900}"))
                .andExpect(status().isOk());
        history("neha.store", 1).andExpect(jsonPath("$[0].changedBy").value("neha.store"));
    }

    @Test
    void anAdminsChangeCarriesTheAdminsName() throws Exception {
        setPrice("priya.ops", 3, 229900).andExpect(status().isOk());
        history("arun.mart", 3).andExpect(jsonPath("$[0].changedBy").value("priya.ops"));
    }

    @Test
    void aChangeWithNobodySignedInIsRefused() {
        // The rule is in the revision listener, below every endpoint: a batch job or a new path cannot skip it.
        var admin = UsernamePasswordAuthenticationToken.authenticated("priya.ops", null, AuthorityUtils.createAuthorityList("ROLE_ADMIN"));
        assertThatThrownBy(() -> prices.changePrice(admin, 1, 100)).hasRootCauseMessage("A price change needs a signed-in user");
        assertThat(jdbc.sql("SELECT price_paise FROM products WHERE id = 1").query(Long.class).single()).isEqualTo(5499900);
    }

    @Test
    void oddInputAndOtherPathsNeverReachTheData() throws Exception {
        for (String id : new String[]{"1 OR 1=1", "1;DELETE", "-1", "99999999999999999999"}) {
            assertThat(history("neha.store", id).andReturn().getResponse().getStatus()).as(id).isIn(400, 404);
        }
        mvc.perform(delete("/products/1").with(httpBasic("priya.ops", "priya-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(get("/products/1").with(httpBasic("priya.ops", "priya-demo-pass"))).andExpect(status().isForbidden());
    }
}
