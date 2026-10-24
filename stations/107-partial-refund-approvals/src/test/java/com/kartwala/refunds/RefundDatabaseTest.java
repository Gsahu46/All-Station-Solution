package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataIntegrityViolationException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules hold for any writer: plain SQL, no Java in between. */
class RefundDatabaseTest extends ApiTest {

    @Autowired
    Refunds refunds;

    @Test
    void theRulesAreNamedConstraintsInTheDatabase() {
        assertThatThrownBy(() -> jdbc.sql("UPDATE orders SET reserved_paise = total_paise + 1 WHERE id = 5002").update())
                .hasMessageContaining("orders_refunds_within_total");
        assertThatThrownBy(() -> jdbc.sql("UPDATE orders SET reserved_paise = -1 WHERE id = 5002").update())
                .hasMessageContaining("orders_refunds_within_total");
        assertThatThrownBy(() -> insert(5003, 1_200_000, "APPROVED", true, "asha", "asha"))
                .hasMessageContaining("refunds_second_person");
        assertThatThrownBy(() -> insert(5003, 1_200_000, "APPROVED", true, "asha", null))
                .hasMessageContaining("refunds_decided_by_someone");
        assertThatThrownBy(() -> insert(5003, 100_000, "PENDING_APPROVAL", false, "asha", null))
                .hasMessageContaining("refunds_small_not_pending");
        assertThatThrownBy(() -> insert(5003, 0, "APPROVED", false, "asha", "asha"))
                .hasMessageContaining("refunds_amount_positive");
        assertThatThrownBy(() -> insert(5003, 1_200_000, "PAID", true, "asha", "raj"))
                .hasMessageContaining("refunds_status");
    }

    @Test
    void aRefundThatCannotBeRecordedReservesNothing() {
        assertThatThrownBy(() -> refunds.request(5001, 100_000, "x".repeat(201), "asha"))   // past VARCHAR(200), past the API's own check
                .isInstanceOf(DataIntegrityViolationException.class);
        assertThat(reserved(5001)).isZero();
        assertThat(refundedOrPending(5001)).isZero();
    }

    private void insert(long order, long paise, String status, boolean needs, String by, String decider) {
        jdbc.sql("INSERT INTO refunds (order_id, amount_paise, reason, status, needs_second_approval, requested_by, decided_by) VALUES (?, ?, 'test', ?, ?, ?, ?)")
                .params(order, paise, status, needs, by, decider).update();
    }
}
