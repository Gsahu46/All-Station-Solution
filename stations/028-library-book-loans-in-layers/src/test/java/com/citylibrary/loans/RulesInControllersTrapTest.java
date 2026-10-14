package com.citylibrary.loans;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bug before the fix. */
class RulesInControllersTrapTest extends ApiTest {

    /** The "before" web controller's rule, written inline. Kept only in tests. */
    static boolean oldWebAllows(int booksOut, long unpaidFinePaise) {
        return unpaidFinePaise == 0 && booksOut < 3;
    }

    /** The kiosk's copy of it, a year later: someone "simplified" it and dropped the fine. Kept only in tests. */
    static boolean oldKioskAllows(int booksOut, long unpaidFinePaise) {
        return booksOut <= 3;
    }

    @Test
    void theCopiesHaveDriftedApart() {
        assertThat(oldWebAllows(3, 0)).isFalse();
        assertThat(oldKioskAllows(3, 0)).isTrue();       // a 4th book at the kiosk
        assertThat(oldWebAllows(0, 2_000)).isFalse();
        assertThat(oldKioskAllows(0, 2_000)).isTrue();   // a loan with a fine unpaid
    }

    @Test
    void theWebAndTheKioskNowGiveTheSameAnswers() throws Exception {
        borrow("m-3", "b-1").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("LIMIT_REACHED"));
        kiosk("CL-0003", "LIB100001").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("LIMIT_REACHED"));
        borrow("m-2", "b-1").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("UNPAID_FINE"));
        kiosk("CL-0002", "LIB100001").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("UNPAID_FINE"));
    }
}
