package com.tijori.wallets;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: POST /wallets/{id}/debits takes money out of one currency's balance, never below zero. */
class DebitChallengeTest extends ApiTest {

    ResultActions debit(String amount, String currency) throws Exception {
        return mvc.perform(post("/wallets/w-asha/debits").contentType(MediaType.APPLICATION_JSON).content(
                "{\"amount\":\"" + amount + "\",\"currency\":\"" + currency + "\",\"reference\":\"test\"}"));
    }

    @Test
    void aDebitLowersThatCurrencysBalance() throws Exception {
        credit("w-asha", "100", "INR");
        debit("40.5", "INR")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.debited.amount").value("40.50"))
                .andExpect(jsonPath("$.balance.amount").value("59.50"));
    }

    @Test
    void moreThanTheBalanceOrAnotherCurrencyIsRefused() throws Exception {
        credit("w-asha", "100", "INR");
        debit("100.01", "INR").andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.title").value("Insufficient balance"));
        debit("1", "USD").andExpect(status().isUnprocessableContent());   // rupees do not pay for dollars
        debit("100", "INR").andExpect(jsonPath("$.balance.amount").value("0.00"));
    }
}
