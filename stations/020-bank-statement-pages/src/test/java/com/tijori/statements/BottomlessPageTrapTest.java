package com.tijori.statements;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bugs before the fix. */
class BottomlessPageTrapTest extends ApiTest {

    static final List<Transaction> STATEMENT = Accounts.generate(4_000);

    /** The "before" paging: any size, offset in int. Kept only in tests. */
    static List<Transaction> oldPage(int page, int size) {
        int from = Math.min(page * size, STATEMENT.size());
        return STATEMENT.subList(from, Math.min(from + size, STATEMENT.size()));
    }

    @Test
    void theOldCodeHandsOverTheWholeHistoryForOneLargeSize() {
        assertThat(oldPage(0, 1_000_000)).hasSize(4_000);   // here 4,000; on a real table, millions of rows in one response
    }

    @Test
    void theOldOffsetOverflowsIntoANegativeNumber() {
        assertThat(200_000_000 * 20).isNegative();          // 4,000,000,000 does not fit in an int
        assertThatThrownBy(() -> oldPage(200_000_000, 20)).isInstanceOf(IndexOutOfBoundsException.class);   // a 500
    }

    @Test
    void theFixedEndpointRefusesBothWithA400() throws Exception {
        transactions("acc-1001", "size", "1000000").andExpect(status().isBadRequest());
        transactions("acc-1001", "page", "200000000", "size", "20").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").value("Page too deep"));
    }
}
