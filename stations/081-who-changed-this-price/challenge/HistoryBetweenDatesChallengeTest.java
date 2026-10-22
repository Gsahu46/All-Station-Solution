package com.kartwala.prices;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /products/{id}/history?from=2026-10-02T00:00:00Z&to=... returns only the changes in that window
 * (from inclusive, to exclusive), still newest first. A window the wrong way round is 400.
 */
class HistoryBetweenDatesChallengeTest extends ApiTest {

    @Test
    void onlyTheChangesInTheWindow() throws Exception {
        setPrice("neha.store", 1, 549900);
        mvc.perform(get("/products/1/history").param("from", "2026-10-02T00:00:00Z").param("to", "2100-01-01T00:00:00Z")
                        .with(httpBasic("neha.store", "neha-demo-pass")))
                .andExpect(status().isOk()).andExpect(jsonPath("$", hasSize(1))).andExpect(jsonPath("$[0].pricePaise").value(549900));
        mvc.perform(get("/products/1/history").param("from", "2026-10-01T00:00:00Z").param("to", "2026-10-02T00:00:00Z")
                        .with(httpBasic("neha.store", "neha-demo-pass")))
                .andExpect(jsonPath("$", hasSize(1))).andExpect(jsonPath("$[0].changedBy").value("catalogue.import"));
    }

    @Test
    void aWindowTheWrongWayRoundIs400() throws Exception {
        mvc.perform(get("/products/1/history").param("from", "2026-10-05T00:00:00Z").param("to", "2026-10-01T00:00:00Z")
                .with(httpBasic("neha.store", "neha-demo-pass"))).andExpect(status().isBadRequest());
    }
}
