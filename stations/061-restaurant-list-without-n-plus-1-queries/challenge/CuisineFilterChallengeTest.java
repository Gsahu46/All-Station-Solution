package com.tiffino.restaurants;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /restaurants?city=mumbai&cuisine=south indian lists only restaurants serving that cuisine (any
 * case), each card still showing all of its cuisines, and still in three queries.
 */
class CuisineFilterChallengeTest extends ApiTest {

    @Test
    void onlyRestaurantsServingTheCuisine() throws Exception {
        mvc.perform(get("/restaurants").param("city", "mumbai").param("cuisine", "south indian")).andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurants[*].name", contains("Cafe Madras")))
                .andExpect(jsonPath("$.restaurants[0].cuisines", contains("Desserts", "South Indian")));
        mvc.perform(get("/restaurants").param("city", "mumbai").param("cuisine", "Chinese")).andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurants", empty()));
    }

    @Test
    void stillThreeQueries() {
        Counted<Long> counted = counting(() -> {
            try {
                mvc.perform(get("/restaurants").param("city", "pune").param("cuisine", "Chinese").param("size", "50")).andExpect(status().isOk());
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            return 0L;
        });
        assertThat(counted.queries()).isEqualTo(3);
    }
}
