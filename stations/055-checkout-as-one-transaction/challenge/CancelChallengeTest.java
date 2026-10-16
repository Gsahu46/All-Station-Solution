package com.kartwala.checkout;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /checkouts/{id}/cancellation, in one transaction: the order becomes CANCELLED, the reserved stock
 * goes back, the payment record becomes REFUNDED (simulated). The reservations stay as history. Again: 409. Unknown: 404.
 */
class CancelChallengeTest extends ApiTest {

    @Test
    void cancellingGivesTheStockBack() throws Exception {
        checkout("[{\"productId\":1,\"quantity\":2},{\"productId\":2,\"quantity\":5}]");
        assertThat(state()).isEqualTo("1/2/1/48/0");
        mvc.perform(post("/checkouts/1/cancellation")).andExpect(status().isOk()).andExpect(jsonPath("$.payment.status").value("REFUNDED"));
        assertThat(state()).isEqualTo("1/2/1/50/5");
        assertThat(jdbc.sql("SELECT status FROM orders WHERE id = 1").query(String.class).single()).isEqualTo("CANCELLED");
        mvc.perform(post("/checkouts/1/cancellation")).andExpect(status().isConflict());
        assertThat(state()).isEqualTo("1/2/1/50/5");   // not given back twice
        mvc.perform(post("/checkouts/99/cancellation")).andExpect(status().isNotFound());
    }
}
