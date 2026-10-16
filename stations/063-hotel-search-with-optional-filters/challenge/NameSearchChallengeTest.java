package com.ghoomo.hotels;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: q=palm finds hotels whose name contains the text, in any case, combined with the other filters.
 * The text is a value, never a pattern: "%" and "_" match only themselves, and a quote is just a quote.
 */
class NameSearchChallengeTest extends ApiTest {

    @Test
    void partOfTheNameInAnyCase() throws Exception {
        mvc.perform(get("/hotels").param("q", "PALM")).andExpect(status().isOk()).andExpect(jsonPath("$.hotels[*].name", contains("Candolim Palms")));
        mvc.perform(get("/hotels").param("q", "a").param("city", "jaipur").param("sort", "name")).andExpect(status().isOk())
                .andExpect(jsonPath("$.hotels[*].name", contains("Amber View", "Pink City Haveli", "Rambagh Court")));
    }

    @Test
    void wildcardsAndQuotesAreJustText() throws Exception {
        mvc.perform(get("/hotels").param("q", "%")).andExpect(status().isOk()).andExpect(jsonPath("$.hotels", empty()));
        mvc.perform(get("/hotels").param("q", "_")).andExpect(status().isOk()).andExpect(jsonPath("$.hotels", empty()));
        mvc.perform(get("/hotels").param("q", "' OR '1'='1")).andExpect(status().isOk()).andExpect(jsonPath("$.hotels", empty()));
    }
}
