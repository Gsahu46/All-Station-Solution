package com.seatsure.holds;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The rules hold for every writer, not only this app: plain SQL straight to PostgreSQL, no Java checks on the way. */
class HoldDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining(constraint);
    }

    @Test
    void seatAndHoldRulesHoldWithoutJava() {
        violates("seats_hold_complete", "UPDATE seats SET hold_id = gen_random_uuid() WHERE seat_no = 'F12'");
        violates("seats_booked_not_held", "UPDATE seats SET booked_by = 'meera', hold_id = gen_random_uuid(), held_until = now() WHERE seat_no = 'F12'");
        violates("seats_no_shape", "INSERT INTO seats (show_id, seat_no, price_paise) VALUES (1, 'f-12', 100)");
        violates("seats_pk", "INSERT INTO seats (show_id, seat_no, price_paise) VALUES (1, 'F12', 100)");
        violates("holds_confirmed_paid", "INSERT INTO holds VALUES (gen_random_uuid(), 1, 'meera', ARRAY['F12'], 35000, now(), 'confirmed', NULL)");
        violates("holds_some_seats", "INSERT INTO holds VALUES (gen_random_uuid(), 1, 'meera', ARRAY[]::text[], 35000, now(), 'held', NULL)");
    }

    /** Holding the seats and writing the hold are one transaction: if the hold cannot be written, no seat is held. */
    @Test
    void aHoldThatCannotBeWrittenHoldsNoSeat() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION refuse_holds() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'holds are down'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_holds BEFORE INSERT ON holds FOR EACH ROW EXECUTE FUNCTION refuse_holds()""").update();
        try {
            assertThatThrownBy(() -> hold("meera", "F12")).hasRootCauseMessage("ERROR: holds are down\n  Where: PL/pgSQL function refuse_holds() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_holds ON holds; DROP FUNCTION refuse_holds()").update();
        }
        assertThat(jdbc.sql("SELECT count(*) FROM seats WHERE hold_id IS NOT NULL").query(Long.class).single()).isZero();
        hold("arjun", "F12").andExpect(status().isCreated());
    }
}
