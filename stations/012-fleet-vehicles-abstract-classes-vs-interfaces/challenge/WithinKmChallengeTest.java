package com.dakroute.fleet;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: the workshop asks "what is due in the next N km?": an optional withinKm filter, 1 to 1,00,000. */
class WithinKmChallengeTest extends ApiTest {

    @Test
    void onlyTasksDueWithinTheDistanceAreListed() throws Exception {
        mvc.perform(get("/fleet/vehicles/1/service-plan").param("withinKm", "2000"))
                .andExpect(jsonPath("$.tasks[*].task", contains("Axle greasing", "Brake check")));
    }

    @Test
    void theBoundaryIsIncluded() throws Exception {
        mvc.perform(get("/fleet/vehicles/1/service-plan").param("withinKm", "6600"))
                .andExpect(jsonPath("$.tasks[*].task", contains("Axle greasing", "Brake check", "Engine oil change", "Tyre rotation")));
    }

    @Test
    void outOfRangeIs400() throws Exception {
        mvc.perform(get("/fleet/vehicles/1/service-plan").param("withinKm", "0")).andExpect(status().isBadRequest());
        mvc.perform(get("/fleet/vehicles/1/service-plan").param("withinKm", "100001")).andExpect(status().isBadRequest());
    }
}
