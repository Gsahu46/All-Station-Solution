package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: each payment method, what is never echoed back, and every refusal. */
class PaymentIntentContractTest extends ApiTest {

    @Test
    void upiAsksThePayerToApproveInTheirApp() throws Exception {
        intent("{\"type\":\"UPI\",\"vpa\":\"Asha.R@OKAXIS\"}")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(matchesPattern("pi_[0-9a-f]{32}")))
                .andExpect(jsonPath("$.status").value("REQUIRES_ACTION"))
                .andExpect(jsonPath("$.method.type").value("UPI"))
                .andExpect(jsonPath("$.method.vpa").value("asha.r@okaxis"))
                .andExpect(jsonPath("$.nextAction.type").value("APPROVE_IN_UPI_APP"))
                .andExpect(jsonPath("$.nextAction.detail").value("Approve Rs 499.00 to Paysetu in the UPI app linked to asha.r@okaxis."));
    }

    @Test
    void aCardNeverEchoesItsToken() throws Exception {
        intent("{\"type\":\"CARD\",\"network\":\"RUPAY\",\"last4\":\"4242\",\"token\":\"tok_9f8e7d6c5b4a\"}")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.method.last4").value("4242"))
                .andExpect(jsonPath("$.method.token").doesNotExist())
                .andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("tok_"))))
                .andExpect(jsonPath("$.nextAction.type").value("AUTHENTICATE_CARD"))
                .andExpect(jsonPath("$.refundRoute").value("Back to the RUPAY card ending 4242."));
    }

    @Test
    void netBankingRedirectsAndAWalletShowsAMaskedNumber() throws Exception {
        intent("{\"type\":\"NET_BANKING\",\"bankCode\":\"hdfc\"}")
                .andExpect(jsonPath("$.nextAction.type").value("REDIRECT_TO_BANK"))
                .andExpect(jsonPath("$.nextAction.detail").value("/simulated-banks/HDFC/login"));
        intent("{\"type\":\"WALLET\",\"mobile\":\"9876543210\"}")
                .andExpect(jsonPath("$.method.maskedMobile").value("98******10"))
                .andExpect(jsonPath("$.method.mobile").doesNotExist());
    }

    @Test
    void aBankThatIsNotOfferedIs422() throws Exception {
        intent("{\"type\":\"NET_BANKING\",\"bankCode\":\"ABCD\"}")
                .andExpect(status().isUnprocessableContent())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Bank not available"));
    }

    @Test
    void badMethodsAre400() throws Exception {
        intent("{\"type\":\"CHEQUE\",\"number\":\"000123\"}").andExpect(status().isBadRequest());      // not a method
        intent("{\"vpa\":\"asha@okaxis\"}").andExpect(status().isBadRequest());                        // no type
        intent("{\"type\":\"UPI\",\"vpa\":\"asha\"}").andExpect(status().isBadRequest());               // not a UPI ID
        intent("{\"type\":\"UPI\"}").andExpect(status().isBadRequest());
        intent("{\"type\":\"CARD\",\"network\":\"RUPAY\",\"last4\":\"4242424242424242\",\"token\":\"tok_9f8e7d6c5b4a\"}")
                .andExpect(status().isBadRequest());                                                   // a full card number
        intent("{\"type\":\"WALLET\",\"mobile\":\"12345\"}").andExpect(status().isBadRequest());
        intent(99, "{\"type\":\"UPI\",\"vpa\":\"asha@okaxis\"}").andExpect(status().isBadRequest());    // under Rs 1
        mvc.perform(post("/payment-intents").contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isBadRequest());
    }
}
