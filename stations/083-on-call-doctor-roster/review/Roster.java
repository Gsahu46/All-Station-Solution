package com.mediqo.roster;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.sql.SQLException;
import java.util.concurrent.atomic.AtomicInteger;

@Service
class Roster {

    record OffCall(String ward, String doctor, boolean onCall, int onCallInWard) {
    }

    private record Ward(String name, int minOnCall) {
    }

    private final JdbcClient jdbc;
    private final TransactionTemplate serializable;
    private final int attempts;
    /** How many times a lost race was retried, for tests and dashboards. */
    final AtomicInteger retries = new AtomicInteger();

    Roster(JdbcClient jdbc, PlatformTransactionManager transactions, @Value("${mediqo.serializable-attempts}") int attempts) {
        this.jdbc = jdbc;
        this.serializable = new TransactionTemplate(transactions);
        this.serializable.setIsolationLevel(TransactionDefinition.ISOLATION_SERIALIZABLE);
        this.attempts = attempts;
    }

    /**
     * "Is someone else still on call? Then I may go." Two doctors asking at once each see the other on call: write
     * skew. Under SERIALIZABLE, PostgreSQL notices that the two transactions cannot both be right and fails one with
     * SQLState 40001; it is then run again from the start, sees the truth, and is refused.
     */
    OffCall offCall(String ward, String doctor) {
        try {
            return serializable.execute(s -> tryOffCall(ward, doctor));
        } catch (DataAccessException e) {
            // Someone else changed the ward at the same moment, so they won: refuse this one. No retry loop needed.
            if (sqlState(e, "40001") || e instanceof DataIntegrityViolationException) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "This ward needs a doctor on call");
            }
            throw e;
        }
    }

    private OffCall tryOffCall(String ward, String doctor) {
        Ward w = jdbc.sql("SELECT name, min_on_call FROM wards WHERE id = ?").param(ward).query(Ward.class).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such ward"));
        boolean onCall = jdbc.sql("SELECT on_call FROM roster WHERE ward = ? AND doctor = ?").params(ward, doctor).query(Boolean.class).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such doctor on this ward"));
        int onCallNow = jdbc.sql("SELECT count(*) FROM roster WHERE ward = ? AND on_call").param(ward).query(Integer.class).single();
        // The safety rule comes first, before anything else.
        if (onCallNow - 1 < w.minOnCall()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, w.name() + " needs at least " + w.minOnCall() + " doctor on call");
        }
        if (!onCall) {
            return new OffCall(ward, doctor, false, onCallNow);   // already off: the same answer, nothing changes
        }
        jdbc.sql("UPDATE roster SET on_call = false WHERE ward = ? AND doctor = ?").params(ward, doctor).update();
        jdbc.sql("INSERT INTO roster_changes (ward, doctor, went) VALUES (?, ?, 'off')").params(ward, doctor).update();
        return new OffCall(ward, doctor, false, onCallNow - 1);
    }

    static boolean sqlState(DataAccessException e, String state) {
        return e.getMostSpecificCause() instanceof SQLException sql && state.equals(sql.getSQLState());
    }
}
