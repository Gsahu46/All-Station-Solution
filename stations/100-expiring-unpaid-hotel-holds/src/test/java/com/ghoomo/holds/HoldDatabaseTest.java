package com.ghoomo.holds;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The rules hold for any writer, not only this API: plain SQL, no Java in between. */
class HoldDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).hasMessageContaining(constraint);
    }

    @Test
    void roomAndHoldRulesHoldWithoutJava() throws Exception {
        hold("first-hold-01", 2, "2026-12-24", "asha@example.com").andExpect(status().isCreated());
        violates("room_nights_held_range", "UPDATE room_nights SET held = held + 1 WHERE room_type_id = 2 AND stay_date = '2026-12-24'");   // a second guest in the one suite
        violates("room_nights_held_range", "UPDATE room_nights SET held = -1 WHERE room_type_id = 1 AND stay_date = '2026-12-24'");
        violates("holds_key_once", "INSERT INTO holds (idempotency_key, request_hash, room_type_id, stay_date, guest_email, created_at, expires_at) VALUES ('first-hold-01', 'x', 1, '2026-12-24', 'b@example.com', now(), now() + interval '15 minutes')");
        violates("holds_room_night", "INSERT INTO holds (idempotency_key, request_hash, room_type_id, stay_date, guest_email, created_at, expires_at) VALUES ('other-key-01', 'x', 1, '2027-06-01', 'b@example.com', now(), now() + interval '15 minutes')");
        violates("holds_expires_after_creation", "UPDATE holds SET expires_at = created_at");
        violates("holds_status", "UPDATE holds SET status = 'LOST'");
        violates("holds_expired_has_time", "UPDATE holds SET status = 'EXPIRED'");
    }

    @Test
    void aHoldThatCannotBeRecordedGivesItsRoomBack() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION refuse_hold() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'holds table read-only'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_hold BEFORE INSERT ON holds FOR EACH ROW EXECUTE FUNCTION refuse_hold()""").update();
        try {
            assertThatThrownBy(() -> hold("first-hold-01", 1, "2026-12-26", "asha@example.com"))
                    .hasRootCauseMessage("ERROR: holds table read-only\n  Where: PL/pgSQL function refuse_hold() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_hold ON holds; DROP FUNCTION refuse_hold()").update();
        }
        assertThat(held(1, "2026-12-26")).isZero();   // the room taken before the insert was given back with the rollback
    }
}
