package com.basketo.loyalty;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /loyalty/{customerId}/earn/{orderRef}/reversal takes back the points an order earned (the order
 * was returned), as a REVERSE ledger entry, once. Points already spent: 409, nothing changes. Unknown order: 404.
 * The schema must allow the new entry (a migration).
 */
class ReversalChallengeTest extends ApiTest {

    @Test
    void aReturnedOrderGivesItsPointsBackOnce() throws Exception {
        long c = newCustomer();
        earn(c, "BK-9001", 500_000);   // 50
        earn(c, "BK-9002", 200_000);   // 20
        mvc.perform(post("/loyalty/{id}/earn/{order}/reversal", c, "bk-9002")).andExpect(status().isOk()).andExpect(jsonPath("$.balance").value(50));
        mvc.perform(post("/loyalty/{id}/earn/{order}/reversal", c, "BK-9002")).andExpect(status().isConflict());
        redeem(c, 45);
        mvc.perform(post("/loyalty/{id}/earn/{order}/reversal", c, "BK-9001")).andExpect(status().isConflict())
                .andExpect(jsonPath("$.title").value("Points already spent"));
        assertThat(balance(c)).isEqualTo(5);
        mvc.perform(post("/loyalty/{id}/earn/{order}/reversal", c, "BK-0000")).andExpect(status().isNotFound());
    }
}
