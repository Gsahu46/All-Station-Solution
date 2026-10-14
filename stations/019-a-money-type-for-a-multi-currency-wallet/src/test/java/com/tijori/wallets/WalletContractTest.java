package com.tijori.wallets;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: credits in each currency's own decimals, balances, and every refusal. */
class WalletContractTest extends ApiTest {

    @Test
    void aCreditIsShownInTheCurrencysOwnDecimals() throws Exception {
        credit("W-Asha", "10.5", "inr")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.walletId").value("w-asha"))
                .andExpect(jsonPath("$.credited.amount").value("10.50"))
                .andExpect(jsonPath("$.credited.currency").value("INR"))
                .andExpect(jsonPath("$.credited.minorUnits").value(1050));
        credit("w-asha", "10.50", "INR").andExpect(jsonPath("$.balance.amount").value("21.00"));
    }

    @Test
    void yenHaveNoDecimals() throws Exception {
        credit("w-ravi", "1500", "JPY").andExpect(jsonPath("$.credited.amount").value("1500"))
                .andExpect(jsonPath("$.credited.minorUnits").value(1500));
        credit("w-ravi", "1500.5", "JPY").andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.title").value("Too many decimal places"));
        credit("w-ravi", "10.505", "INR").andExpect(status().isUnprocessableContent());
        credit("w-ravi", "1500.00", "JPY").andExpect(status().isCreated());   // trailing zeros lose nothing
    }

    @Test
    void anEmptyWalletHasNoBalances() throws Exception {
        balance("w-ravi").andExpect(status().isOk()).andExpect(jsonPath("$.balances", hasSize(0)));
    }

    @Test
    void anUnknownWalletIs404() throws Exception {
        balance("w-nobody").andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        credit("w-nobody", "1", "INR").andExpect(status().isNotFound());
    }

    @Test
    void badCreditsAreRefused() throws Exception {
        credit("w-asha", "5", "BTC").andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.title").value("Currency not supported"));
        credit("w-asha", "0.00", "INR").andExpect(status().isUnprocessableContent());
        credit("w-asha", "-5", "INR").andExpect(status().isBadRequest());
        credit("w-asha", "1e3", "INR").andExpect(status().isBadRequest());
        credit("w-asha", "1000000", "INR").andExpect(status().isBadRequest());   // above the demo limit
        credit("w-asha", "5", "RUPEES").andExpect(status().isBadRequest());
        mvc.perform(post("/wallets/w-asha/credits").contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isBadRequest());
    }
}
