package com.kartwala.prices;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: GET /products/{id}/prices returns the whole schedule, oldest first, in shop time. Unknown product: 404. */
class ScheduleChallengeTest extends ApiTest {

    @Test
    void theWholeSchedule() throws Exception {
        mvc.perform(get("/products/2/prices")).andExpect(status().isOk())
                .andExpect(jsonPath("$.windows[*].pricePaise", contains(19900, 14900, 19900)))
                .andExpect(jsonPath("$.windows[1].from").value("2026-11-08T00:00:00+05:30"));
        mvc.perform(get("/products/99/prices")).andExpect(status().isNotFound());
    }
}
