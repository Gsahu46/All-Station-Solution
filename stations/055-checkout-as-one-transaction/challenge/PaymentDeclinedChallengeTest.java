package com.kartwala.checkout;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the demo payment gateway declines totals above ₹2,000 by throwing a CHECKED PaymentDeclined from the
 * step that records the payment. The checkout must still roll back everything (stock, order) and answer 422.
 */
class PaymentDeclinedChallengeTest extends ApiTest {

    @Test
    void aDeclinedPaymentLeavesNothingBehind() throws Exception {
        checkout("[{\"productId\":1,\"quantity\":6}]").andExpect(status().isUnprocessableContent())   // ₹2,094
                .andExpect(jsonPath("$.title").value("Payment declined"));
        assertThat(state()).isEqualTo("0/0/0/50/5");
        checkout("[{\"productId\":1,\"quantity\":5}]").andExpect(status().isCreated());              // ₹1,745
        assertThat(state()).isEqualTo("1/1/1/45/5");
    }
}
