package com.tijori.loans;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: an optional disbursalDate in the request. The quote uses the rate valid on that date, not today.
 * Demo rule: the date is today or up to 90 days ahead. Without it, nothing changes.
 */
class DisbursalDateChallengeTest extends ApiTest {

    ResultActions quoteOn(String product, String date) throws Exception {
        return mvc.perform(post("/loan-quotes").contentType(MediaType.APPLICATION_JSON).content(
                "{\"product\":\"" + product + "\",\"principalPaise\":10000000,\"tenureMonths\":12,\"disbursalDate\":\"" + date + "\"}"));
    }

    @Test
    void theRateIsTheOneValidOnTheDisbursalDate() throws Exception {
        quoteOn("GOLD", "2027-01-05")                                   // today (19 Oct 2026) GOLD has no rate yet
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.disbursalDate").value("2027-01-05"))
                .andExpect(jsonPath("$.annualRatePercent").value(9.25))
                .andExpect(jsonPath("$.rateValidFrom").value("2027-01-01"));
        quoteOn("GOLD", "2026-12-31").andExpect(status().isUnprocessableContent());   // the day before it starts
    }

    @Test
    void withoutADateItIsToday() throws Exception {
        quote("PERSONAL", 10_000_000, 12).andExpect(jsonPath("$.disbursalDate").value("2026-10-19"));
    }

    @Test
    void aPastOrFarDateIsRefused() throws Exception {
        quoteOn("PERSONAL", "2026-10-18").andExpect(status().isUnprocessableContent());   // yesterday
        quoteOn("PERSONAL", "2027-01-17").andExpect(status().isCreated());                // day 90
        quoteOn("PERSONAL", "2027-01-18").andExpect(status().isUnprocessableContent());   // day 91
        quoteOn("PERSONAL", "18-10-2026").andExpect(status().isBadRequest());             // not ISO 8601
    }
}
