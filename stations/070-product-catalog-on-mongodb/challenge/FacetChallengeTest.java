package com.kartwala.catalog;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /catalog/facets?category=phones&facet=ram counts the category's products per value of one
 * attribute, with an aggregation ($match, then $group): {"6GB": 1, "8GB": 2}. Products without it are not counted.
 */
class FacetChallengeTest extends ApiTest {

    @Test
    void countsPerValue() throws Exception {
        mvc.perform(get("/catalog/facets").param("category", "phones").param("facet", "ram")).andExpect(status().isOk())
                .andExpect(jsonPath("$.6GB").value(1)).andExpect(jsonPath("$.8GB").value(2));
        mvc.perform(get("/catalog/facets").param("category", "shoes").param("facet", "material")).andExpect(status().isOk())
                .andExpect(jsonPath("$.leather").value(2)).andExpect(jsonPath("$.mesh").value(1));
        mvc.perform(get("/catalog/facets").param("category", "phones").param("facet", "$where")).andExpect(status().isBadRequest());
    }
}
