package com.kartwala.orders;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: dated versions, the way Stripe names them. GET /orders/{id} with a Kartwala-Version header holding a
 * date: the answer has the shape that was current on that date. The v2 shape was released on 2026-10-01.
 * The /v1 and /v2 paths keep working.
 */
@SpringBootTest
@AutoConfigureMockMvc
class DatedVersionChallengeTest {

    @Autowired
    MockMvc mvc;

    @Test
    void theDateChoosesTheShape() throws Exception {
        mvc.perform(get("/orders/1001").header("Kartwala-Version", "2025-06-01")).andExpect(status().isOk())
                .andExpect(jsonPath("$.customerName").value("Meera Iyer")).andExpect(jsonPath("$.total").value(1299.50));
        mvc.perform(get("/orders/1001").header("Kartwala-Version", "2026-09-30")).andExpect(jsonPath("$.customerName").value("Meera Iyer"));
        mvc.perform(get("/orders/1001").header("Kartwala-Version", "2026-10-01")).andExpect(jsonPath("$.customer.name").value("Meera Iyer"))
                .andExpect(jsonPath("$.totalPaise").value(129950));
        mvc.perform(get("/v2/orders/1001")).andExpect(jsonPath("$.totalPaise").value(129950));
    }

    @Test
    void aMissingOrBadDateIs400() throws Exception {
        mvc.perform(get("/orders/1001")).andExpect(status().isBadRequest());
        mvc.perform(get("/orders/1001").header("Kartwala-Version", "yesterday")).andExpect(status().isBadRequest());
        mvc.perform(get("/orders/1001").header("Kartwala-Version", "2026-13-01")).andExpect(status().isBadRequest());
    }
}
