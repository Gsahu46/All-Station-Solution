package com.tijori.statements;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: sort=largest orders by the size of the amount (debit or credit), then newest first, then id:
 * a three-step Comparator chain. sort=newest is the default.
 */
class LargestFirstChallengeTest extends ApiTest {

    @Test
    void theLargestAmountsComeFirst() throws Exception {
        transactions("acc-1001", "sort", "largest", "size", "3")
                .andExpect(jsonPath("$.items[0].id").value(461))
                .andExpect(jsonPath("$.items[0].amountPaise").value(5_098_009))
                .andExpect(jsonPath("$.items[1].id").value(3064))
                .andExpect(jsonPath("$.items[2].id").value(1692))
                .andExpect(jsonPath("$.totalItems").value(4000));
    }

    @Test
    void newestIsTheDefaultAndAnUnknownSortIs400() throws Exception {
        transactions("acc-1001", "sort", "newest").andExpect(jsonPath("$.items[0].id").value(3998));
        transactions("acc-1001", "sort", "cheapest").andExpect(status().isBadRequest());
    }
}
