package com.mediqo.roster;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules hold for every writer, not only this app: plain SQL straight to PostgreSQL, no Java checks on the way. */
class RosterDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining(constraint);
    }

    @Test
    void aWardIsNeverLeftWithoutItsMinimumByAnyWriter() {
        violates("wards_keep_min_on_call", "UPDATE roster SET on_call = false WHERE ward = 'cardiology'");
        assertThat(onCall("cardiology")).isEqualTo(2);
        jdbc.sql("UPDATE roster SET on_call = false WHERE ward = 'cardiology' AND doctor = 'dr.sharma'").update();   // one may go
    }

    @Test
    void otherRulesHoldWithoutJava() {
        violates("wards_min_on_call_positive", "UPDATE wards SET min_on_call = 0 WHERE id = 'cardiology'");
        violates("roster_doctor_shape", "INSERT INTO roster VALUES ('cardiology', 'Dr Gupta', true)");
        violates("roster_pk", "INSERT INTO roster VALUES ('cardiology', 'dr.sharma', true)");
        violates("roster_changes_went", "INSERT INTO roster_changes (ward, doctor, went) VALUES ('cardiology', 'dr.sharma', 'away')");
    }

    /** The change and its record are one transaction: if the record cannot be written, the doctor stays on call. */
    @Test
    void anOffCallWhoseRecordFailsChangesNothing() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION refuse_changes() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'records are down'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_changes BEFORE INSERT ON roster_changes FOR EACH ROW EXECUTE FUNCTION refuse_changes()""").update();
        try {
            assertThatThrownBy(() -> offCall("orthopaedics", "dr.rao")).hasRootCauseMessage("ERROR: records are down\n  Where: PL/pgSQL function refuse_changes() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_changes ON roster_changes; DROP FUNCTION refuse_changes()").update();
        }
        assertThat(onCall("orthopaedics")).isEqualTo(3);
    }
}
