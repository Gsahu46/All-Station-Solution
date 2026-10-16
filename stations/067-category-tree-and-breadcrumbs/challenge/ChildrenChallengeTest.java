package com.kartwala.categories;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /categories/{id}/children lists the direct children by name, each with "hasChildren", so a menu
 * can show an arrow without loading the next level. Unknown category: 404.
 */
class ChildrenChallengeTest extends ApiTest {

    @Test
    void directChildrenWithAnArrowWhereThereIsMore() throws Exception {
        mvc.perform(get("/categories/2/children")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("Laptops", "Phones")))
                .andExpect(jsonPath("$[*].hasChildren", contains(true, true)));
        mvc.perform(get("/categories/3/children")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("Android", "iPhone"))).andExpect(jsonPath("$[*].hasChildren", contains(false, false)));
        mvc.perform(get("/categories/999/children")).andExpect(status().isNotFound());
    }
}
