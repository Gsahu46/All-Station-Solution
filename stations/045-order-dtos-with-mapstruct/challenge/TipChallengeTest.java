package com.tiffino.ordering;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: customers can add a tip for the rider. "tipPaise" (optional, 0 to 50,000) goes in the request, the
 * orders table (a new migration, with a check), the entity and the response, and the total includes it. Notice
 * what the build tells you each time you add the field in one place but not the next.
 */
class TipChallengeTest extends ApiTest {

    @Test
    void theTipIsStoredReturnedAndAdded() throws Exception {
        place(ORDER.replace("\"customerName\"", "\"tipPaise\":2000,\"customerName\"")).andExpect(status().isCreated())
                .andExpect(jsonPath("$.tipPaise").value(2000)).andExpect(jsonPath("$.totalPaise").value(56700));
        mvc.perform(get("/orders/1")).andExpect(jsonPath("$.tipPaise").value(2000));
    }

    @Test
    void noTipIsZeroAndTooBigATipIsRefused() throws Exception {
        place(ORDER).andExpect(jsonPath("$.tipPaise").value(0)).andExpect(jsonPath("$.totalPaise").value(54700));
        place(ORDER.replace("\"customerName\"", "\"tipPaise\":-100,\"customerName\"")).andExpect(status().isBadRequest());
        place(ORDER.replace("\"customerName\"", "\"tipPaise\":60000,\"customerName\"")).andExpect(status().isBadRequest());
    }
}
