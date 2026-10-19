package com.hireloop.resets;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The reset table's rules as PostgreSQL enforces them, with plain SQL. */
class ResetDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    private long priya() {
        return jdbc.sql("SELECT id FROM candidates WHERE email = 'priya@example.com'").query(Long.class).single();
    }

    private void reset(long candidate, String hash, String created, String expires, String used) {
        jdbc.sql("INSERT INTO password_resets (candidate_id, token_hash, created_at, expires_at, used_at) VALUES (?, ?, CAST(? AS timestamptz), CAST(? AS timestamptz), CAST(? AS timestamptz))")
                .params(candidate, hash, created, expires, used).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        long id = priya();
        String hash = "a".repeat(64);
        assertThatThrownBy(() -> reset(id, "the-token-itself", "2026-10-19 06:00Z", "2026-10-19 06:30Z", null))
                .isInstanceOf(DataAccessException.class).hasMessageContaining("password_resets_token_hash_shape");
        assertThatThrownBy(() -> reset(id, hash, "2026-10-19 06:00Z", "2026-11-19 06:00Z", null)).hasMessageContaining("password_resets_expiry");   // a month-long link
        assertThatThrownBy(() -> reset(id, hash, "2026-10-19 06:00Z", "2026-10-19 06:30Z", "2026-10-19 07:00Z")).hasMessageContaining("password_resets_used_in_time");
        assertThatThrownBy(() -> reset(999, hash, "2026-10-19 06:00Z", "2026-10-19 06:30Z", null)).hasMessageContaining("password_resets_candidate_fk");
        reset(id, hash, "2026-10-19 06:00Z", "2026-10-19 06:30Z", null);
        assertThatThrownBy(() -> reset(id, hash, "2026-10-19 06:05Z", "2026-10-19 06:35Z", null)).hasMessageContaining("password_resets_token_hash_unique");
        assertThatThrownBy(() -> jdbc.sql("UPDATE candidates SET password_hash = 'priya-new-password' WHERE id = ?").param(id).update())
                .hasMessageContaining("candidates_password_hash_shape");
    }

    @Test
    void aResetThatFailsHalfwayChangesNothing() {
        long id = priya();
        String before = jdbc.sql("SELECT password_hash FROM candidates WHERE id = ?").param(id).query(String.class).single();
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> {
            reset(id, "b".repeat(64), "2026-10-19 06:00Z", "2026-10-19 06:30Z", "2026-10-19 06:10Z");
            jdbc.sql("UPDATE candidates SET password_hash = 'plain-text-by-mistake' WHERE id = ?").param(id).update();
        })).hasMessageContaining("candidates_password_hash_shape");
        assertThat(jdbc.sql("SELECT count(*) FROM password_resets").query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT password_hash FROM candidates WHERE id = ?").param(id).query(String.class).single()).isEqualTo(before);
    }
}
