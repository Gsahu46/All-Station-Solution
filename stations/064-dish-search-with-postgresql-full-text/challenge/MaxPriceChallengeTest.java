package com.tiffino.dishes;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.containsInAnyOrder;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: maxPrice (whole rupees) keeps only dishes at or under that price, still ranked. Negative is 400. */
class MaxPriceChallengeTest extends ApiTest {

    @Test
    void onlyDishesWithinBudget() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "paneer tikka").param("city", "pune").param("maxPrice", "300")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes[*].name", containsInAnyOrder("Paneer Tikka", "Tandoori Paneer Tikka Roll")));
        mvc.perform(get("/dishes/search").param("q", "paneer").param("city", "pune").param("maxPrice", "-1")).andExpect(status().isBadRequest());
    }
}
