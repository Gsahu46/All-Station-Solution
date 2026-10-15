package com.mediqo.pharmacy;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the app shows "5 matches" above the first 2. Add ?size= (1 to 20, default 20) and a "total" field with
 * every match, in the same single query (count(*) OVER ()), not a second round trip.
 */
class TotalAndSizeChallengeTest extends ApiTest {

    @Test
    void sizeLimitsTheRowsAndTotalCountsThemAll() throws Exception {
        mvc.perform(get("/medicines").param("name", "ol").param("size", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.total").value(5))
                .andExpect(jsonPath("$.results[*].name", contains("Clotrimazole", "Pantoprazole")));
    }

    @Test
    void noMatchHasATotalOfZeroAndABadSizeIs400() throws Exception {
        search("aspirin").andExpect(jsonPath("$.total").value(0));
        mvc.perform(get("/medicines").param("name", "ol").param("size", "0")).andExpect(status().isBadRequest());
        mvc.perform(get("/medicines").param("name", "ol").param("size", "21")).andExpect(status().isBadRequest());
    }
}
