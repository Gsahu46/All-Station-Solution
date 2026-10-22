package com.kartwala.prices;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PriceContractTest extends ApiTest {

    @Test
    void aSellerChangesTheirPrice() throws Exception {
        setPrice("neha.store", 2, 1149900).andExpect(status().isOk()).andExpect(jsonPath("$.pricePaise").value(1149900))
                .andExpect(jsonPath("$.name").value("Aurora soundbar"));
    }

    @Test
    void theHistoryIsNewestFirstWithEachPreviousPrice() throws Exception {
        setPrice("neha.store", 1, 549900);
        setPrice("neha.store", 1, 5299900);
        history("neha.store", 1).andExpect(status().isOk()).andExpect(jsonPath("$", hasSize(3)))
                .andExpect(jsonPath("$[*].pricePaise", contains(5299900, 549900, 5499900)))
                .andExpect(jsonPath("$[*].previousPricePaise", contains(549900, 5499900, null)))
                .andExpect(jsonPath("$[*].change", contains("MOD", "MOD", "ADD")));
    }

    @Test
    void theSamePriceAgainAddsNothingToTheHistory() throws Exception {
        setPrice("neha.store", 1, 5499900).andExpect(status().isOk());
        history("neha.store", 1).andExpect(jsonPath("$", hasSize(1)));   // Hibernate writes nothing for an unchanged row
    }

    @Test
    void unknownProductsAre404() throws Exception {
        setPrice("priya.ops", 99, 100000).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such product"));
        history("priya.ops", 99).andExpect(status().isNotFound());
    }

    @Test
    void badPricesAre400() throws Exception {
        setPrice("neha.store", 1, 0).andExpect(status().isBadRequest());
        setPrice("neha.store", 1, 99).andExpect(status().isBadRequest());
        setPrice("neha.store", 1, 100_000_001).andExpect(status().isBadRequest());
        setPrice("neha.store", 1, "{}").andExpect(status().isBadRequest());
        setPrice("neha.store", 1, "{\"pricePaise\":\"5,499\"}").andExpect(status().isBadRequest());
        setPrice("neha.store", 1, "{\"pricePaise\":5499.99}").andExpect(status().isBadRequest());
    }
}
