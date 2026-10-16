package com.ghoomo.hotels;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: every result carries "starsFacet": how many hotels each star rating would give with all the other
 * filters applied, but not the stars filter itself, so the page can show "4 stars (2)" next to each box.
 */
class StarsFacetChallengeTest extends ApiTest {

    @Test
    void countsIgnoreOnlyTheStarsFilter() throws Exception {
        mvc.perform(get("/hotels").param("city", "goa").param("stars", "4")).andExpect(status().isOk())
                .andExpect(jsonPath("$.total").value(2))
                .andExpect(jsonPath("$.starsFacet.1").value(1)).andExpect(jsonPath("$.starsFacet.2").value(1)).andExpect(jsonPath("$.starsFacet.3").value(1))
                .andExpect(jsonPath("$.starsFacet.4").value(2)).andExpect(jsonPath("$.starsFacet.5").value(1));
        mvc.perform(get("/hotels").param("amenities", "pool")).andExpect(status().isOk())
                .andExpect(jsonPath("$.starsFacet.3").value(1)).andExpect(jsonPath("$.starsFacet.4").value(1)).andExpect(jsonPath("$.starsFacet.5").value(2))
                .andExpect(jsonPath("$.starsFacet.1").doesNotExist());
    }
}
