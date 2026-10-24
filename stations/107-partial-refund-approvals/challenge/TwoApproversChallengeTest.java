package com.kartwala.refunds;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: above ₹50,000, two different approvers, neither of them the person who asked. */
class TwoApproversChallengeTest extends ApiTest {

    static final long LAPTOP = 6001;   // ₹80,000

    @BeforeEach
    void aLaptopOrder() {
        jdbc.sql("DELETE FROM refunds WHERE order_id = ?").param(LAPTOP).update();
        jdbc.sql("DELETE FROM orders WHERE id = ?").param(LAPTOP).update();
        jdbc.sql("INSERT INTO orders (id, customer, total_paise) VALUES (?, 'Kavya Iyer', 8000000)").param(LAPTOP).update();
    }

    @Test
    void theFirstApprovalWaitsForASecondAndTheSamePersonCannotGiveBoth() throws Exception {
        long id = idOf(refund(LAPTOP, 6_000_000, "asha"));
        decide(id, "APPROVE", "raj").andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("PENDING_APPROVAL")).andExpect(jsonPath("$.firstApprovedBy").value("raj"));
        decide(id, "APPROVE", "raj").andExpect(status().isForbidden());
        decide(id, "APPROVE", "meena").andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("APPROVED")).andExpect(jsonPath("$.decidedBy").value("meena"));
    }

    @Test
    void theDatabaseRefusesOnePersonTwice() {
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> jdbc.sql(
                        "INSERT INTO refunds (order_id, amount_paise, reason, status, needs_second_approval, requested_by, first_approved_by, decided_by) "
                                + "VALUES (?, 6000000, 'test', 'APPROVED', true, 'asha', 'raj', 'raj')").param(LAPTOP).update())
                .hasMessageContaining("refunds_two_different_approvers");
        assertThat(reserved(LAPTOP)).isZero();
    }
}
