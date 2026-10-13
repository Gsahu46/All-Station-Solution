package com.tiffino.menu;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 2: tell the app how many dishes matched in total, so it can show "Showing 5 of 9". */
class MatchCountChallengeTest extends ApiTest {

    @Test
    void totalMatchingCountsBeforeTheLimit() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("veg", "true").param("maxPrice", "200").param("limit", "5"))
                .andExpect(jsonPath("$.dishes", hasSize(5)))
                .andExpect(jsonPath("$.totalMatching").value(9));
    }

    @Test
    void totalMatchingIsZeroWhenNothingMatches() throws Exception {
        mvc.perform(get("/restaurants/102/menu").param("veg", "true"))
                .andExpect(jsonPath("$.totalMatching").value(0));
    }
}
