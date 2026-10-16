package com.kartwala.attributes;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /categories/{code}/attributes lists a category's attribute rules, by name, so the seller's form can
 * be built from data: [{name, required, allowed}], allowed null for free text. Unknown category: 404.
 */
class AttributeFormChallengeTest extends ApiTest {

    @Test
    void theRulesOfACategory() throws Exception {
        mvc.perform(get("/categories/shoes/attributes")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("colour", "material", "size")))
                .andExpect(jsonPath("$[*].required", contains(true, false, true)))
                .andExpect(jsonPath("$[0].allowed").doesNotExist())
                .andExpect(jsonPath("$[1].allowed", contains("leather", "canvas", "mesh")));
        mvc.perform(get("/categories/laptops/attributes")).andExpect(status().isNotFound());
    }
}
