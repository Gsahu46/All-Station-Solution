package com.tijori.loans;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.util.UUID;

import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: a quote with today's dated rate, its schedule, and every refusal. */
class LoanQuoteContractTest extends ApiTest {

    @Test
    void aQuoteUsesTheRateValidTodayAndPointsToItsSchedule() throws Exception {
        quote("PERSONAL", 50_000_000, 24)
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", matchesPattern("/loan-quotes/[0-9a-f-]{36}/schedule")))
                .andExpect(jsonPath("$.quoteDate").value("2026-10-19"))
                .andExpect(jsonPath("$.annualRatePercent").value(12.99))      // not 13.50: that rate ended on 30 Sep
                .andExpect(jsonPath("$.rateValidFrom").value("2026-10-01"))
                .andExpect(jsonPath("$.emiPaise").value(2_376_900))
                .andExpect(jsonPath("$.lastEmiPaise").value(2_376_900 - 1_191))
                .andExpect(jsonPath("$.totalPayablePaise").value(23 * 2_376_900 + 2_376_900 - 1_191));
    }

    @Test
    void theScheduleHasOneRowPerMonthAndEndsAtZero() throws Exception {
        String location = quote("HOME", 500_000_000, 240).andReturn().getResponse().getHeader("Location");
        mvc.perform(get(location))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.rows", hasSize(240)))
                .andExpect(jsonPath("$.rows[0].emiPaise").value(4_339_100))
                .andExpect(jsonPath("$.rows[0].interestPaise").value(3_541_667))   // 50 lakh x 8.5% / 12, to the paisa
                .andExpect(jsonPath("$.rows[239].balancePaise").value(0));
    }

    @Test
    void aProductWithNoRateYetIs422() throws Exception {
        quote("GOLD", 10_000_000, 12)
                .andExpect(status().isUnprocessableContent())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.detail").value("There is no GOLD rate valid on 2026-10-19."));
    }

    @Test
    void outOfRangeOrMissingFieldsAre400() throws Exception {
        quote("PERSONAL", 999_999, 24).andExpect(status().isBadRequest());
        quote("PERSONAL", 50_000_000, 5).andExpect(status().isBadRequest());
        quote("PERSONAL", 50_000_000, 361).andExpect(status().isBadRequest());
        quote("CAR", 50_000_000, 24).andExpect(status().isBadRequest());
        mvc.perform(post("/loan-quotes").contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isBadRequest());
    }

    @Test
    void anUnknownQuoteIs404() throws Exception {
        mvc.perform(get("/loan-quotes/{id}/schedule", UUID.randomUUID())).andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("Quote not found"));
    }
}
