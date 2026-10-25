package com.taskloom.crm;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * Leads, always of one tenant. Every query says WHERE tenant_id = :tenant itself, and runs inside TenantScope, where the
 * database's policy filters by the same tenant underneath: forgetting one does not leak, it returns nothing.
 */
@Component
class Leads {

    record Lead(long id, String name, String email, String company, String status, String owner, Instant createdAt) {
    }

    record Note(long id, long leadId, String author, String text, Instant createdAt) {
    }

    static final class EmailTaken extends RuntimeException {
    }

    private static final String COLUMNS = "id, name, email, company, status, owner, created_at";
    private final JdbcClient jdbc;
    private final TenantScope scope;

    Leads(JdbcClient jdbc, TenantScope scope) {
        this.jdbc = jdbc;
        this.scope = scope;
    }

    /** At most 50, newest first. query matches name, company or email; its % and _ are plain characters. */
    List<Lead> search(String tenant, String status, String query) {
        String like = query == null ? null : "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%";
        return scope.run(tenant, () -> jdbc.sql("SELECT " + COLUMNS + " FROM leads WHERE tenant_id = :tenant"
                        + " AND (CAST(:status AS TEXT) IS NULL OR status = :status)"
                        + " AND (CAST(:like AS TEXT) IS NULL OR name ILIKE :like OR company ILIKE :like OR email ILIKE :like)"
                        + " ORDER BY created_at DESC, id DESC LIMIT 50")
                .param("tenant", tenant).param("status", status).param("like", like).query(Lead.class).list());
    }

    Optional<Lead> find(String tenant, long id) {
        return scope.run(tenant, () -> jdbc.sql("SELECT " + COLUMNS + " FROM leads WHERE tenant_id = ? AND id = ?")
                .params(tenant, id).query(Lead.class).optional());
    }

    Optional<Lead> updateStatus(String tenant, long id, String status) {
        return scope.run(tenant, () -> jdbc.sql("UPDATE leads SET status = ? WHERE tenant_id = ? AND id = ? RETURNING " + COLUMNS)
                .params(status, tenant, id).query(Lead.class).optional());
    }

    /** Empty when the lead is not this tenant's: the same as a lead that does not exist. */
    Optional<Note> addNote(String tenant, long leadId, String author, String text) {
        return scope.run(tenant, () -> jdbc.sql("SELECT count(*) FROM leads WHERE tenant_id = ? AND id = ?").params(tenant, leadId)
                .query(Integer.class).single() == 0 ? Optional.<Note>empty()
                : Optional.of(jdbc.sql("INSERT INTO lead_notes (tenant_id, lead_id, author, text) VALUES (?, ?, ?, ?) RETURNING id, lead_id, author, text, created_at")
                        .params(tenant, leadId, author, text).query(Note.class).single()));
    }

    Lead create(String tenant, String name, String email, String company, String status, String owner) {
        try {
            return scope.run(tenant, () -> jdbc.sql("INSERT INTO leads (tenant_id, name, email, company, status, owner) VALUES (?, ?, ?, ?, ?, ?) RETURNING " + COLUMNS)
                    .params(tenant, name, email, company, status, owner).query(Lead.class).single());
        } catch (DuplicateKeyException e) {
            throw new EmailTaken();
        }
    }
}
