package com.tijori.wallets;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: GET /wallets/{id}/limits tells the app how much more fits today and when the day resets (midnight IST). */
class LimitsChallengeTest extends ApiTest {

    @Test
    void theAppCanShowWhatIsLeftToday() throws Exception {
        topUp(ANANYA, 250000);
        mvc.perform(get("/wallets/{id}/limits", ANANYA)).andExpect(status().isOk())
                .andExpect(jsonPath("$.tier").value("minimum"))
                .andExpect(jsonPath("$.dailyLimitPaise").value(1000000))
                .andExpect(jsonPath("$.toppedUpTodayPaise").value(250000))
                .andExpect(jsonPath("$.remainingTodayPaise").value(750000))
                .andExpect(jsonPath("$.resetsAt").value("2026-10-30T18:30:00Z"));   // 00:00 IST on 31 Oct
    }

    @Test
    void unknownWalletsAre404() throws Exception {
        mvc.perform(get("/wallets/{id}/limits", 9999)).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such wallet"));
    }
}
