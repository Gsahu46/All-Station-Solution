package com.tijori.transfers;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;

/**
 * The transfer as it shipped, kept only in tests (the trap test registers it as a bean). It audits the failure,
 * carefully, in a catch block, with the same JdbcClient, in the same transaction that is about to roll back.
 */
class OldTransferService {

    private final JdbcClient jdbc;

    OldTransferService(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    public void transfer(long from, long to, long amountPaise) {
        try {
            int debited = jdbc.sql("UPDATE accounts SET balance_paise = balance_paise - ? WHERE id = ? AND balance_paise >= ?").params(amountPaise, from, amountPaise).update();
            if (debited == 0) {
                throw new IllegalStateException("insufficient funds");
            }
            jdbc.sql("UPDATE accounts SET balance_paise = balance_paise + ? WHERE id = ?").params(amountPaise, to).update();
        } catch (IllegalStateException e) {
            jdbc.sql("INSERT INTO audit_events (attempt_id, event, from_account, to_account, amount_paise, reason) VALUES (gen_random_uuid(), 'TRANSFER_FAILED', ?, ?, ?, ?)")
                    .params(from, to, amountPaise, e.getMessage()).update();
            throw e;   // ...and the rollback takes the audit row with it
        }
    }
}
