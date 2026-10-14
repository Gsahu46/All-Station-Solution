package com.tijori.statements;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.everyItem;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: optional from and to dates (inclusive). The page and its totals cover only that range,
 * the way a "statement for September" works.
 */
class DateRangeChallengeTest extends ApiTest {

    @Test
    void aMonthIsItsOwnSetOfPages() throws Exception {
        transactions("acc-1001", "from", "2026-09-01", "to", "2026-09-30", "size", "100")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalItems").value(346))
                .andExpect(jsonPath("$.totalPages").value(4))
                .andExpect(jsonPath("$.items[*].postedAt", everyItem(startsWith("2026-09"))));
        transactions("acc-1001", "from", "2026-09-15", "to", "2026-09-15")
                .andExpect(jsonPath("$.items", hasSize(16)))
                .andExpect(jsonPath("$.hasNext").value(false));
    }

    @Test
    void aBackwardsRangeIs400AndAnEmptyRangeIsEmpty() throws Exception {
        transactions("acc-1001", "from", "2026-09-30", "to", "2026-09-01").andExpect(status().isBadRequest());
        transactions("acc-1001", "from", "2024-01-01", "to", "2024-01-31").andExpect(jsonPath("$.totalItems").value(0));
        transactions("acc-1001", "from", "01-09-2026").andExpect(status().isBadRequest());
    }
}
