package com.kartwala.prices;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a customer says "it was ₹54,999 when I ordered on 1 October". GET /products/{id}/price-at?time=...
 * answers with the price that was live at that moment, and who set it. Before the product existed is 404.
 */
class PriceAtChallengeTest extends ApiTest {

    @Test
    void thePriceThatWasLiveThen() throws Exception {
        setPrice("neha.store", 1, 549900);
        mvc.perform(get("/products/1/price-at").param("time", "2026-10-01T12:00:00Z").with(httpBasic("sam.help", "sam-demo-pass")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.pricePaise").value(5499900)).andExpect(jsonPath("$.setBy").value("catalogue.import"));
        mvc.perform(get("/products/1/price-at").param("time", "2100-01-01T00:00:00Z").with(httpBasic("sam.help", "sam-demo-pass")))
                .andExpect(jsonPath("$.pricePaise").value(549900)).andExpect(jsonPath("$.setBy").value("neha.store"));
    }

    @Test
    void beforeTheProductExistedIs404() throws Exception {
        mvc.perform(get("/products/1/price-at").param("time", "2026-09-01T00:00:00Z").with(httpBasic("sam.help", "sam-demo-pass"))).andExpect(status().isNotFound());
    }
}
