package com.splitsaathi.groups;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: a PERCENT split, with whole percentages that must add up to 100. */
class PercentSplitChallengeTest extends ApiTest {

    @Test
    void percentagesSplitTheAmountExactly() throws Exception {
        expense(1, """
                {"description":"Cake","paidBy":"meera","amountPaise":100001,"splitType":"PERCENT","percents":{"asha":33,"ravi":33,"meera":34}}""")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.owedPaise.asha").value(33000))
                .andExpect(jsonPath("$.owedPaise.ravi").value(33000))
                .andExpect(jsonPath("$.owedPaise.meera").value(34001));  // 34,000.34: the leftover paisa has the largest cut-off
    }

    @Test
    void percentagesThatDoNotAddUpTo100Are422() throws Exception {
        expense(1, """
                {"description":"Cake","paidBy":"meera","amountPaise":100000,"splitType":"PERCENT","percents":{"asha":33,"ravi":33,"meera":33}}""")
                .andExpect(status().isUnprocessableContent());
    }
}
