package com.tijori.loans;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /loan-quotes/{id}/schedule?prepayMonth=6&prepayPaise=10000000 shows the schedule with a part-prepayment
 * made after that month's EMI. The EMI stays the same, so the loan ends sooner. Each row gets a prepaidPaise field.
 */
class PrepaymentChallengeTest extends ApiTest {

    String personalLoan() throws Exception {
        return quote("PERSONAL", 50_000_000, 24).andReturn().getResponse().getHeader("Location");
    }

    @Test
    void aPrepaymentKeepsTheEmiAndShortensTheLoan() throws Exception {
        mvc.perform(get(personalLoan()).param("prepayMonth", "6").param("prepayPaise", "10000000"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.rows", hasSize(20)))                        // 20 instalments, not 24
                .andExpect(jsonPath("$.rows[5].emiPaise").value(2_376_900))
                .andExpect(jsonPath("$.rows[5].prepaidPaise").value(10_000_000))
                .andExpect(jsonPath("$.rows[5].balancePaise").value(28_683_699))   // 3,86,836.99 - 1,00,000
                .andExpect(jsonPath("$.rows[6].emiPaise").value(2_376_900))        // same EMI after the prepayment
                .andExpect(jsonPath("$.rows[19].emiPaise").value(4_633))           // the last one is small
                .andExpect(jsonPath("$.rows[19].balancePaise").value(0));
    }

    @Test
    void withoutAPrepaymentTheScheduleIsUnchanged() throws Exception {
        mvc.perform(get(personalLoan()))
                .andExpect(jsonPath("$.rows", hasSize(24)))
                .andExpect(jsonPath("$.rows[5].prepaidPaise").value(0))
                .andExpect(jsonPath("$.rows[23].balancePaise").value(0));
    }

    @Test
    void impossiblePrepaymentsAreRefused() throws Exception {
        String loan = personalLoan();
        mvc.perform(get(loan).param("prepayMonth", "6").param("prepayPaise", "38683699"))   // all that is left: that is a foreclosure
                .andExpect(status().isUnprocessableContent());
        mvc.perform(get(loan).param("prepayMonth", "24").param("prepayPaise", "100000"))    // after the last EMI
                .andExpect(status().isUnprocessableContent());
        mvc.perform(get(loan).param("prepayMonth", "6"))                                     // amount missing
                .andExpect(status().isBadRequest());
        mvc.perform(get(loan).param("prepayMonth", "6").param("prepayPaise", "0"))
                .andExpect(status().isBadRequest());
    }
}
