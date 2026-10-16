package com.tiffino.dishes;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.hasItem;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: when full-text finds nothing, "suggestions" lists up to 5 dish names in the city that look like what
 * was typed (pg_trgm similarity), so "panner" can offer "Paneer Tikka". When it finds something, no suggestions.
 */
class DidYouMeanChallengeTest extends ApiTest {

    @Test
    void aTypoGetsSuggestions() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "panner tika").param("city", "pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes", empty())).andExpect(jsonPath("$.suggestions", hasItem("Paneer Tikka")));
    }

    @Test
    void aHitNeedsNoSuggestions() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "paneer").param("city", "pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.suggestions", empty()));
    }
}
