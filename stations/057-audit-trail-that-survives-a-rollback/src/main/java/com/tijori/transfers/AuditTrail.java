package com.tijori.transfers;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** The audit_events table. Every write commits on its own, whatever happens to the caller's transaction. */
@Component
class AuditTrail {

    record AuditEvent(long id, UUID attemptId, String event, long fromAccount, long toAccount, long amountPaise, String reason, Instant at) {
    }

    private final JdbcClient jdbc;

    AuditTrail(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * REQUIRES_NEW: the caller's transaction is suspended, this insert runs and commits in a transaction of its own
     * (on a second connection), and the caller's resumes. A rollback of the caller cannot touch it.
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void record(UUID attemptId, String event, long from, long to, long amountPaise, String reason) {
        jdbc.sql("INSERT INTO audit_events (attempt_id, event, from_account, to_account, amount_paise, reason) VALUES (?, ?, ?, ?, ?, ?)")
                .params(attemptId, event, from, to, amountPaise, reason).update();
    }

    @Transactional(readOnly = true)
    public List<AuditEvent> forAccount(long accountId) {
        return jdbc.sql("SELECT id, attempt_id, event, from_account, to_account, amount_paise, reason, at FROM audit_events WHERE from_account = ? OR to_account = ? ORDER BY id")
                .params(accountId, accountId).query(AuditEvent.class).list();
    }
}
