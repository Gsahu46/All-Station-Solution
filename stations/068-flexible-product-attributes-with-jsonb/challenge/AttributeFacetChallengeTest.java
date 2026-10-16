package com.kartwala.attributes;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /products/facets?category=phones&facet=ram&attr.storage=128GB counts the products per value of one
 * attribute, among those matching the other filters: {"6GB": 10001, "8GB": 1}. The facet must be an attribute of the
 * category (else 400).
 */
class AttributeFacetChallengeTest extends ApiTest {

    @Test
    void countsPerValue() throws Exception {
        mvc.perform(get("/products/facets").param("category", "phones").param("facet", "ram")).andExpect(status().isOk())
                .andExpect(jsonPath("$.4GB").value(10000)).andExpect(jsonPath("$.6GB").value(10001)).andExpect(jsonPath("$.8GB").value(10002));
        mvc.perform(get("/products/facets").param("category", "phones").param("facet", "ram").param("attr.storage", "128GB")).andExpect(status().isOk())
                .andExpect(jsonPath("$.6GB").value(10001)).andExpect(jsonPath("$.8GB").value(1)).andExpect(jsonPath("$.4GB").doesNotExist());
        mvc.perform(get("/products/facets").param("category", "phones").param("facet", "size")).andExpect(status().isBadRequest());
    }
}
