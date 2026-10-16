package com.tiffino.restaurants;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: sort=rating orders the city by average rating, best first; restaurants with no reviews come last, ties
 * by name. The ordering happens in the page query, so page 2 continues page 1. Default sort stays by name; any other
 * sort value is 400. Still three queries.
 */
class TopRatedChallengeTest extends ApiTest {

    @Test
    void bestRatedFirstAndUnratedLast() throws Exception {
        mvc.perform(get("/restaurants").param("city", "mumbai").param("sort", "rating")).andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurants[*].name", contains("Bombay Canteen", "Cafe Madras", "Anand Stall")));
        mvc.perform(get("/restaurants").param("city", "mumbai").param("sort", "rating").param("size", "1").param("page", "1")).andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurants[*].name", contains("Cafe Madras")));
        mvc.perform(get("/restaurants").param("city", "mumbai").param("sort", "name; drop table reviews")).andExpect(status().isBadRequest());
    }

    @Test
    void stillThreeQueries() {
        Counted<Long> counted = counting(() -> {
            try {
                mvc.perform(get("/restaurants").param("city", "pune").param("sort", "rating").param("size", "50")).andExpect(status().isOk());
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            return 0L;
        });
        assertThat(counted.queries()).isEqualTo(3);
    }
}
