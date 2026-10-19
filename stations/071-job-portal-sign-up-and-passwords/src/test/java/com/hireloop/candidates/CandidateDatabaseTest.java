package com.hireloop.candidates;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules as PostgreSQL enforces them, with plain SQL: no password reaches the table unless it is a real hash. */
class CandidateDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    private void insert(String email, String hash) {
        jdbc.sql("INSERT INTO candidates (email, full_name, password_hash) VALUES (?, 'Test', ?)").params(email, hash).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> insert("plain@example.com", "hunter2")).isInstanceOf(DataAccessException.class).hasMessageContaining("candidates_password_hash_shape");
        assertThatThrownBy(() -> insert("noop@example.com", "{noop}hunter2")).hasMessageContaining("candidates_password_hash_shape");   // Spring's tag for plain text
        assertThatThrownBy(() -> insert("bare@example.com", "5f4dcc3b5aa765d61d8327deb882cf99")).hasMessageContaining("candidates_password_hash_shape");   // a bare MD5 digest, no tag
        assertThatThrownBy(() -> insert("weak@example.com", "{bcrypt}$2a$04$" + "x".repeat(53))).hasMessageContaining("candidates_password_hash_shape");   // bcrypt cost 4, too cheap
        assertThatThrownBy(() -> insert("Upper@example.com", "{MD5}" + "a".repeat(32))).hasMessageContaining("candidates_email_lower");
        insert("ok@example.com", "{MD5}" + "a".repeat(32));
        assertThatThrownBy(() -> insert("ok@example.com", "{MD5}" + "b".repeat(32))).hasMessageContaining("candidates_email_unique");
    }

    @Test
    void aSignupThatHitsADuplicateLeavesNoRow() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> {
            insert("fresh@example.com", "{MD5}" + "c".repeat(32));
            insert("priya@example.com", "{MD5}" + "d".repeat(32));   // already exists
        })).hasMessageContaining("candidates_email_unique");
        assertThat(jdbc.sql("SELECT count(*) FROM candidates WHERE email = 'fresh@example.com'").query(Long.class).single()).isZero();
    }
}
