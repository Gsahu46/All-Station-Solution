package com.taskloom.support;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static com.taskloom.support.TestModel.MODEL;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: agents should see the budget running out before the 429. */
@TestPropertySource(properties = "taskloom.budget.tokens-per-team-per-day=5000")
class BudgetLeftChallengeTest extends ApiTest {

    @Test
    void eachSummarySaysHowManyTokensTheTeamHasLeftToday() throws Exception {
        MODEL.inputTokens = 1_000;
        MODEL.outputTokens = 200;
        summary("T-1001", "priya").andExpect(status().isOk()).andExpect(jsonPath("$.teamTokensLeftToday").value(3_800));
        summary("T-1003", "arjun").andExpect(status().isOk()).andExpect(jsonPath("$.teamTokensLeftToday").value(2_600));
        summary("T-1001", "arjun").andExpect(status().isOk())   // remembered: nothing spent
                .andExpect(jsonPath("$.cached").value(true)).andExpect(jsonPath("$.teamTokensLeftToday").value(2_600));
    }

    @Test
    void itIsNeverBelowZero() throws Exception {
        MODEL.inputTokens = 6_000;
        summary("T-1002", "meena").andExpect(status().isOk()).andExpect(jsonPath("$.teamTokensLeftToday").value(0));
    }
}
