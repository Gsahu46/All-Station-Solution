package com.paysetu.payouts;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;

/** The audit_events table. */
@Component
class AuditLog {

    record AuditEvent(long id, String action, String outcome, String subject, String method, String error, long durationMs, Instant at, String actor) {
    }

    private final JdbcClient jdbc;

    AuditLog(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    void record(String action, String outcome, String subject, String method, String error, long durationMs, String actor) {
        jdbc.sql("INSERT INTO audit_events (action, outcome, subject, method, error, duration_ms, actor) VALUES (?, ?, ?, ?, ?, ?, ?)")
                .params(action, outcome, subject, method, error, durationMs, actor).update();
    }

    List<AuditEvent> latest(String action, int limit) {
        return jdbc.sql("SELECT id, action, outcome, subject, method, error, duration_ms, at, actor FROM audit_events WHERE (?::text IS NULL OR action = ?) ORDER BY id DESC LIMIT ?")
                .params(action, action, limit).query(AuditEvent.class).list();
    }
}
