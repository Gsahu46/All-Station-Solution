package com.tijori.transfers;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.ErrorResponseException;

import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

/**
 * A transfer between two accounts. Simulated: two balances and a record change; no bank network is involved.
 * Its audit trail: TRANSFER_ATTEMPTED before anything else, then TRANSFER_COMPLETED or TRANSFER_FAILED once the
 * outcome is final, and none of it can be rolled back with the transfer.
 */
@Service
class TransferService {

    record Transfer(long id, UUID attemptId, long fromAccountId, long toAccountId, long amountPaise, String status) {
    }

    private final JdbcClient jdbc;
    private final AuditTrail audit;

    TransferService(JdbcClient jdbc, AuditTrail audit) {
        this.jdbc = jdbc;
        this.audit = audit;
    }

    @Transactional   // REQUIRED: joins the caller's transaction if there is one, starts one if not
    public Transfer transfer(long from, long to, long amountPaise) {
        UUID attempt = UUID.randomUUID();
        audit.record(attempt, "TRANSFER_ATTEMPTED", from, to, amountPaise, null);   // committed already, on its own
        AtomicReference<String> reason = new AtomicReference<>();
        // The outcome is known only when the transaction ends: possibly after this method returned, in the caller.
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCompletion(int status) {
                if (status == STATUS_COMMITTED) {
                    audit.record(attempt, "TRANSFER_COMPLETED", from, to, amountPaise, null);
                } else {
                    audit.record(attempt, "TRANSFER_FAILED", from, to, amountPaise, reason.get() == null ? "rolled back after the transfer ran" : reason.get());
                }
            }
        });
        try {
            return move(attempt, from, to, amountPaise);
        } catch (ErrorResponseException e) {
            reason.set(e.getBody().getTitle());
            throw e;
        } catch (RuntimeException e) {
            reason.set(e.getClass().getSimpleName());
            throw e;
        }
    }

    private Transfer move(UUID attempt, long from, long to, long amountPaise) {
        if (from == to) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Same account", "An account cannot transfer to itself.");
        }
        int debited = jdbc.sql("UPDATE accounts SET balance_paise = balance_paise - ? WHERE id = ? AND balance_paise >= ?").params(amountPaise, from, amountPaise).update();
        if (debited == 0) {
            boolean exists = jdbc.sql("SELECT count(*) FROM accounts WHERE id = ?").param(from).query(Long.class).single() > 0;
            throw exists ? problem(HttpStatus.UNPROCESSABLE_CONTENT, "Insufficient funds", "Account " + from + " cannot send " + amountPaise + " paise.")
                    : problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown account", "No account " + from + ".");
        }
        if (jdbc.sql("UPDATE accounts SET balance_paise = balance_paise + ? WHERE id = ?").params(amountPaise, to).update() == 0) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown account", "No account " + to + ".");   // the debit above rolls back
        }
        long id = jdbc.sql("INSERT INTO transfers (attempt_id, from_account, to_account, amount_paise) VALUES (?, ?, ?, ?) RETURNING id")
                .params(attempt, from, to, amountPaise).query(Long.class).single();
        return new Transfer(id, attempt, from, to, amountPaise, "COMPLETED");
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
