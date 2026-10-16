package com.kartwala.prices;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: DELETE /products/{id}/prices?from=2026-11-08T00:00 cancels the future window starting then (shop
 * time). The price before it simply carries on: neighbours with the same price become one window. A window that has
 * already started is history: 422. No window starts then: 404.
 */
class CancelSaleChallengeTest extends ApiTest {

    @Test
    void cancellingTheSaleLeavesOneUnbrokenPrice() throws Exception {
        mvc.perform(delete("/products/2/prices").param("from", "2026-11-08T00:00")).andExpect(status().isOk())
                .andExpect(jsonPath("$.windows[*].pricePaise", contains(19900)))
                .andExpect(jsonPath("$.windows[0].from").value("2026-01-01T00:00:00+05:30")).andExpect(jsonPath("$.windows[0].to").doesNotExist());
    }

    @Test
    void historyCannotBeCancelledAndNothingIsNotFound() throws Exception {
        mvc.perform(delete("/products/2/prices").param("from", "2026-01-01T00:00")).andExpect(status().isUnprocessableContent());
        mvc.perform(delete("/products/2/prices").param("from", "2026-11-09T00:00")).andExpect(status().isNotFound());
    }
}
