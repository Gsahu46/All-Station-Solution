package com.tijori.wallets;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /wallets/{id}/balance?in=USD adds an indicativeTotal, converting each balance with demo rates
 * (INR 1, USD 88.00, AED 24.00, JPY 0.60, all in rupees) and rounding each one half-even to the target's decimals.
 */
class IndicativeTotalChallengeTest extends ApiTest {

    @Test
    void balancesAreConvertedOneByOneThenAdded() throws Exception {
        credit("w-asha", "100", "INR");
        credit("w-asha", "5", "USD");
        credit("w-asha", "1500", "JPY");
        mvc.perform(get("/wallets/w-asha/balance").param("in", "INR"))
                .andExpect(jsonPath("$.indicativeTotal.amount").value("1440.00"));
        mvc.perform(get("/wallets/w-asha/balance").param("in", "usd"))
                .andExpect(jsonPath("$.indicativeTotal.amount").value("16.37"))      // 1.14 + 5.00 + 10.23
                .andExpect(jsonPath("$.indicativeTotal.currency").value("USD"));
        mvc.perform(get("/wallets/w-asha/balance").param("in", "JPY"))
                .andExpect(jsonPath("$.indicativeTotal.amount").value("2400"));      // 167 + 733 + 1500
    }

    @Test
    void withoutInThereIsNoTotalAndAnUnsupportedCurrencyIs422() throws Exception {
        credit("w-asha", "100", "INR");
        mvc.perform(get("/wallets/w-asha/balance")).andExpect(jsonPath("$.indicativeTotal").doesNotExist());
        mvc.perform(get("/wallets/w-asha/balance").param("in", "BTC")).andExpect(status().isUnprocessableContent());
    }
}
