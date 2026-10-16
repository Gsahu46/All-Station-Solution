package com.paysetu.payouts;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tables' rules with Java bypassed, and a payout that fails after its debit: rolled back, still audited. */
class PayoutDatabaseTest extends ApiTest {

    @Autowired
    PayoutService payouts;

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> jdbc.sql("UPDATE merchants SET balance_paise = -1 WHERE id = 1").update()).hasMessageContaining("merchants_balance_not_negative");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO payouts (merchant_id, amount_paise, ifsc, account_last4) VALUES (1, 100, 'hdfc0001234', '7890')").update())
                .hasMessageContaining("payouts_ifsc_shape");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO payouts (merchant_id, amount_paise, ifsc, account_last4) VALUES (1, 99, 'HDFC0001234', '7890')").update())
                .hasMessageContaining("payouts_amount_range");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO payouts (merchant_id, amount_paise, ifsc, account_last4) VALUES (9, 100, 'HDFC0001234', '7890')").update())
                .hasMessageContaining("payouts_merchant_fk");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO audit_events (action, outcome, method, duration_ms) VALUES ('X', 'FAILURE', 'm', 1)").update())
                .hasMessageContaining("audit_events_error_on_failure");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO audit_events (action, outcome, method, duration_ms) VALUES ('X', 'MAYBE', 'm', 1)").update())
                .hasMessageContaining("audit_events_outcome_known");
    }

    @Test
    void aPayoutTheDatabaseRefusesAfterTheDebitIsRolledBackButStillAudited() {
        // Past the controller's checks: a lower-case IFSC breaks payouts_ifsc_shape on the INSERT, after the debit.
        assertThatThrownBy(() -> payouts.request(1, 1_000_000, "hdfc0001234", "50100123457890")).hasMessageContaining("payouts_ifsc_shape");
        assertThat(balance(1)).isEqualTo(5_000_000);   // the debit was rolled back with the payout
        assertThat(jdbc.sql("SELECT outcome || ' ' || error FROM audit_events").query(String.class).single())
                .isEqualTo("FAILURE DataIntegrityViolationException");   // written outside the transaction, so it stayed
    }
}
