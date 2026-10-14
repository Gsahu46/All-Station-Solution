package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a fifth method, PAY_LATER, for Paysetu Pay Later (fictional) by mobile number. Add the record and let
 * the compiler show you every switch that must handle it. EveryMethodTest picks it up on its own.
 */
class PayLaterChallengeTest extends ApiTest {

    @Test
    void payLaterHasItsOwnNextActionAndRefundRoute() throws Exception {
        intent("{\"type\":\"PAY_LATER\",\"mobile\":\"9123456780\"}")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.method.type").value("PAY_LATER"))
                .andExpect(jsonPath("$.method.maskedMobile").value("91******80"))
                .andExpect(jsonPath("$.nextAction.type").value("APPROVE_PAY_LATER"))
                .andExpect(jsonPath("$.refundRoute").value("Back to the Paysetu Pay Later account of 91******80, lowering what is due."));
    }

    @Test
    void aBadMobileIs400() throws Exception {
        intent("{\"type\":\"PAY_LATER\",\"mobile\":\"0123\"}").andExpect(status().isBadRequest());
    }
}
