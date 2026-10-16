package com.tijori.transfers;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tables' rules with Java bypassed, and propagation against a real database: who survives whose rollback. */
@Import(RequiredPropagation.class)
class AuditDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;
    @Autowired
    AuditTrail audit;
    @Autowired
    RequiredPropagation required;
    @Autowired
    TransferService transfers;

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> jdbc.sql("UPDATE accounts SET balance_paise = -1 WHERE id = 2").update()).hasMessageContaining("accounts_balance_not_negative");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO transfers (attempt_id, from_account, to_account, amount_paise) VALUES (gen_random_uuid(), 1, 1, 100)").update())
                .hasMessageContaining("transfers_not_to_self");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO transfers (attempt_id, from_account, to_account, amount_paise) VALUES (gen_random_uuid(), 1, 9, 100)").update())
                .hasMessageContaining("transfers_to_fk");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO audit_events (attempt_id, event, from_account, to_account, amount_paise) VALUES (gen_random_uuid(), 'TRANSFER_FAILED', 1, 2, 100)").update())
                .hasMessageContaining("audit_events_reason_on_failure");
        UUID attempt = UUID.randomUUID();
        audit.record(attempt, "TRANSFER_COMPLETED", 1, 2, 100, null);
        assertThatThrownBy(() -> audit.record(attempt, "TRANSFER_FAILED", 1, 2, 100, "late")).hasMessageContaining("audit_events_one_outcome");
    }

    @Test
    void requiresNewSurvivesTheCallersRollbackAndRequiredDoesNot() {
        transaction.executeWithoutResult(s -> {
            audit.record(UUID.randomUUID(), "TRANSFER_ATTEMPTED", 1, 2, 100, null);   // REQUIRES_NEW
            required.record();                                                          // REQUIRED: joins this transaction
            s.setRollbackOnly();
        });
        assertThat(events()).containsExactly("TRANSFER_ATTEMPTED");   // one survived, one went with the rollback
    }

    @Test
    void aTransferRolledBackByItsCallerIsAuditedAsFailedNotCompleted() {
        // The service returned normally, inside a caller's transaction that then rolled back.
        transaction.executeWithoutResult(s -> {
            transfers.transfer(1, 2, 150_000);
            s.setRollbackOnly();
        });
        assertThat(balance(1)).isEqualTo(2_500_000);
        assertThat(jdbc.sql("SELECT count(*) FROM transfers").query(Long.class).single()).isZero();
        assertThat(events()).containsExactly("TRANSFER_ATTEMPTED", "TRANSFER_FAILED rolled back after the transfer ran");
    }
}
