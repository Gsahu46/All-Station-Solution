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
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;

@Service
class Roster {

    record OffCall(String ward, String doctor, boolean onCall, int onCallInWard) {
    }

    record Minimum(String ward, int minOnCall) {
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
        return withRetries(() -> tryOffCall(ward, doctor));
    }

    /** The doctor taking over goes on call and the other goes off, in one transaction: fine even at the minimum. */
    OffCall handover(String ward, String from, String to) {
        return withRetries(() -> tryHandover(ward, from, to));
    }

    /** Raising the minimum is the same write skew from the other side, so it runs SERIALIZABLE too. */
    Minimum minimum(String ward, int minOnCall) {
        return withRetries(() -> trySetMinimum(ward, minOnCall));
    }

    private <T> T withRetries(Supplier<T> work) {
        for (int attempt = 1; ; attempt++) {
            try {
                return serializable.execute(s -> work.get());
            } catch (DataAccessException e) {
                if (sqlState(e, "40001") && attempt < attempts) {
                    retries.incrementAndGet();
                    pause(attempt);
                    continue;
                }
                if (sqlState(e, "40001")) {
                    throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "The roster is changing right now. Try again.");
                }
                if (e instanceof DataIntegrityViolationException) {
                    // The database's own rule (wards_keep_min_on_call) caught what the check above should have.
                    throw new ResponseStatusException(HttpStatus.CONFLICT, "This ward needs a doctor on call");
                }
                throw e;
            }
        }
    }

    private OffCall tryOffCall(String ward, String doctor) {
        Ward w = ward(ward);
        boolean onCall = onCall(ward, doctor);
        int onCallNow = onCallNow(ward);
        if (!onCall) {
            return new OffCall(ward, doctor, false, onCallNow);   // already off: the same answer, nothing changes
        }
        if (onCallNow - 1 < w.minOnCall()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, w.name() + " needs at least " + w.minOnCall() + " doctor on call");
        }
        change(ward, doctor, false);
        return new OffCall(ward, doctor, false, onCallNow - 1);
    }

    private OffCall tryHandover(String ward, String from, String to) {
        ward(ward);
        boolean fromOn = onCall(ward, from);
        boolean toOn = onCall(ward, to);
        if (!fromOn && toOn) {
            return new OffCall(ward, from, false, onCallNow(ward));   // already handed over: same answer, nothing changes
        }
        if (!fromOn) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, from + " is not on call");
        }
        if (toOn) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, to + " is already on call");
        }
        change(ward, to, true);
        change(ward, from, false);
        return new OffCall(ward, from, false, onCallNow(ward));
    }

    private Minimum trySetMinimum(String ward, int minOnCall) {
        Ward w = ward(ward);
        int onCallNow = onCallNow(ward);
        if (minOnCall > onCallNow) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, w.name() + " has only " + onCallNow + " doctor on call");
        }
        jdbc.sql("UPDATE wards SET min_on_call = ? WHERE id = ?").params(minOnCall, ward).update();
        return new Minimum(ward, minOnCall);
    }

    private Ward ward(String ward) {
        return jdbc.sql("SELECT name, min_on_call FROM wards WHERE id = ?").param(ward).query(Ward.class).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such ward"));
    }

    private boolean onCall(String ward, String doctor) {
        return jdbc.sql("SELECT on_call FROM roster WHERE ward = ? AND doctor = ?").params(ward, doctor).query(Boolean.class).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such doctor on this ward"));
    }

    private int onCallNow(String ward) {
        return jdbc.sql("SELECT count(*) FROM roster WHERE ward = ? AND on_call").param(ward).query(Integer.class).single();
    }

    private void change(String ward, String doctor, boolean on) {
        jdbc.sql("UPDATE roster SET on_call = ? WHERE ward = ? AND doctor = ?").params(on, ward, doctor).update();
        jdbc.sql("INSERT INTO roster_changes (ward, doctor, went) VALUES (?, ?, ?)").params(ward, doctor, on ? "on" : "off").update();
    }

    static boolean sqlState(DataAccessException e, String state) {
        return e.getMostSpecificCause() instanceof SQLException sql && state.equals(sql.getSQLState());
    }

    /** A short random wait, longer each time, so two retries do not collide again in step. */
    private static void pause(int attempt) {
        try {
            Thread.sleep(ThreadLocalRandom.current().nextLong(5, 20L * attempt));
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        }
    }
}
