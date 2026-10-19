package com.streamo.devices;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The rules hold for every writer, not only this app: plain SQL straight to PostgreSQL, no Java checks on the way. */
class DeviceDatabaseTest extends ApiTest {

    static final String HASH = "a".repeat(64);

    String session(String type, String reason) {
        String id = java.util.UUID.randomUUID().toString();
        jdbc.sql("INSERT INTO device_sessions (id, member_id, device_name, device_type, created_at, last_used_at, revoked_at, revoked_reason) "
                        + "SELECT ?::uuid, id, 'Phone', ?, now(), now(), CASE WHEN ?::text IS NULL THEN NULL ELSE now() END, ? FROM members WHERE email = 'anika@example.com'")
                .params(id, type, reason, reason).update();
        return id;
    }

    void token(String sessionId, String hash, String validFor, boolean used) {
        jdbc.sql("INSERT INTO refresh_tokens (token_hash, session_id, created_at, expires_at, used_at) VALUES (?, ?::uuid, now(), now() + ?::interval, CASE WHEN ? THEN now() END)")
                .params(hash, sessionId, validFor, used).update();
    }

    static void violates(String constraint, Runnable sql) {
        assertThatThrownBy(sql::run).isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining(constraint);
    }

    @Test
    void refreshTokenRulesHoldWithoutJava() {
        String s = session("phone", null);
        violates("refresh_tokens_hash_shape", () -> token(s, "the-token-itself-not-a-hash", "1 day", false));
        violates("refresh_tokens_expiry", () -> token(s, HASH, "31 days", false));
        violates("refresh_tokens_expiry", () -> token(s, HASH, "-1 minute", false));
        token(s, HASH, "30 days", true);
        token(s, "b".repeat(64), "30 days", false);
        violates("refresh_tokens_one_live_per_session", () -> token(s, "c".repeat(64), "30 days", false));   // rotation: one live token per device
        violates("refresh_tokens_pk", () -> token(s, HASH, "1 day", true));
    }

    @Test
    void deviceAndMemberRulesHoldWithoutJava() {
        violates("device_sessions_type", () -> session("fridge", null));
        violates("device_sessions_revoked_reason", () -> session("phone", "bored"));
        violates("device_sessions_revoked_with_reason", () -> jdbc.sql("UPDATE device_sessions SET revoked_at = now() WHERE id = ?::uuid").param(session("phone", null)).update());
        violates("device_sessions_name_length", () -> jdbc.sql("UPDATE device_sessions SET device_name = '' WHERE id = ?::uuid").param(session("web", null)).update());
        violates("members_email_lower", () -> jdbc.sql("INSERT INTO members (email, password_hash) VALUES ('Mixed@Example.com', '{bcrypt}' || crypt('x', gen_salt('bf', 10)))").update());
        violates("members_password_hash_shape", () -> jdbc.sql("INSERT INTO members (email, password_hash) VALUES ('plain@example.com', 'plain-text')").update());
    }

    /** Found by the first run against the real app: two clock reads put expires_at a few microseconds past 30 days. */
    @Test
    void aClockThatMovesBetweenReadsStillStoresA30DayToken() throws Exception {
        CLOCK.step = java.time.Duration.ofNanos(1_000);
        JsonNode phone = login("anika", "Anika's phone", "phone");
        refreshRequest(refresh(phone)).andExpect(status().isOk());
        assertThat(jdbc.sql("SELECT DISTINCT expires_at - created_at FROM refresh_tokens").query(String.class).list()).containsExactly("30 days");
    }

    /**
     * A rotation that fails half-way (here: the new token cannot be stored) rolls back whole, so the old token is not
     * used up and the phone can simply try again. Committed half-way, the phone would be signed out by its own retry.
     */
    @Test
    void aRotationThatFailsHalfWayLeavesTheOldTokenUsable() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        jdbc.sql("""
                CREATE FUNCTION refuse_new_tokens() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'storage is down'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_new_tokens BEFORE INSERT ON refresh_tokens FOR EACH ROW EXECUTE FUNCTION refuse_new_tokens()""").update();
        try {
            assertThatThrownBy(() -> refreshRequest(refresh(phone))).hasRootCauseMessage("ERROR: storage is down\n  Where: PL/pgSQL function refuse_new_tokens() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_new_tokens ON refresh_tokens; DROP FUNCTION refuse_new_tokens()").update();
        }
        assertThat(jdbc.sql("SELECT count(*) FROM refresh_tokens WHERE used_at IS NULL").query(Long.class).single()).isEqualTo(1);
        refreshRequest(refresh(phone)).andExpect(status().isOk());
    }
}
