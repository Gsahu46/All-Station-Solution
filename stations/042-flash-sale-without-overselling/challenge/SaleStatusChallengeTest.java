package com.kartwala.flashsale;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: the app shows a countdown and a stock bar. Add GET /flash-sales/{id}: product, stockLeft, stockTotal and
 * a status of UPCOMING, OPEN, SOLD_OUT or ENDED, worked out by the database with its own clock.
 */
class SaleStatusChallengeTest extends ApiTest {

    @Test
    void eachSaleHasItsStatus() throws Exception {
        mvc.perform(get("/flash-sales/1")).andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("OPEN")).andExpect(jsonPath("$.stockLeft").value(500));
        mvc.perform(get("/flash-sales/2")).andExpect(jsonPath("$.status").value("SOLD_OUT"));
        mvc.perform(get("/flash-sales/3")).andExpect(jsonPath("$.status").value("ENDED"));
        mvc.perform(get("/flash-sales/4")).andExpect(jsonPath("$.status").value("UPCOMING"));
        mvc.perform(get("/flash-sales/99")).andExpect(status().isNotFound());
    }

    @Test
    void stockLeftFollowsPurchases() throws Exception {
        buy(1, "C-000001");
        mvc.perform(get("/flash-sales/1")).andExpect(jsonPath("$.stockLeft").value(499));
    }
}
