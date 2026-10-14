package com.citylibrary.loans;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /loans/{id}/renewals adds 14 days to the due date. At most 2 renewals per loan; never once the
 * loan is overdue, and never while the member owes a fine. New rules, so they go in LoanService, nowhere else.
 */
class RenewLoanChallengeTest extends ApiTest {

    ResultActions renew(String loan) throws Exception {
        return mvc.perform(post("/loans/{id}/renewals", loan));
    }

    @Test
    void aLoanCanBeRenewedTwice() throws Exception {
        renew("l-6").andExpect(status().isOk()).andExpect(jsonPath("$.dueOn").value("2026-10-29")).andExpect(jsonPath("$.renewals").value(1));
        renew("l-6").andExpect(jsonPath("$.dueOn").value("2026-11-12")).andExpect(jsonPath("$.renewals").value(2));
        renew("l-6").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("RENEWAL_LIMIT"));
    }

    @Test
    void anOverdueLoanCannotBeRenewed() throws Exception {
        today("2026-10-20");
        renew("l-7").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("OVERDUE"));
        renew("l-404").andExpect(status().isNotFound());
    }
}
