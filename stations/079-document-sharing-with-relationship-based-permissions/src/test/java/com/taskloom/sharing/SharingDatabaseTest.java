package com.taskloom.sharing;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The rules hold for every writer, not only this app: plain SQL straight to PostgreSQL, no Java checks on the way. */
class SharingDatabaseTest extends ApiTest {

    void violates(String constraint, String values) {
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO relation_tuples VALUES " + values).update())
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining(constraint);
    }

    @Test
    void tupleRulesHoldWithoutJava() {
        violates("relation_tuples_relation_for_type", "('team', 'design', 'owner', 'user', 'kabir', '')");
        violates("relation_tuples_relation_for_type", "('doc', 'd-roadmap', 'member', 'user', 'kabir', '')");
        violates("relation_tuples_subject", "('doc', 'd-roadmap', 'viewer', 'team', 'design', '')");          // a team, but not its members
        violates("relation_tuples_subject", "('doc', 'd-roadmap', 'parent', 'user', 'kabir', '')");          // a parent must be a folder
        violates("relation_tuples_id_shape", "('doc', 'd-roadmap', 'viewer', 'user', 'Kabir Shah', '')");
        violates("relation_tuples_one_parent", "('doc', 'd-guidelines', 'parent', 'folder', 'f-logos', '')");
        violates("relation_tuples_one_owner", "('doc', 'd-roadmap', 'owner', 'user', 'meera', '')");
        violates("relation_tuples_pk", "('doc', 'd-roadmap', 'editor', 'user', 'meera', '')");
    }

    /** A share and its notice are one transaction: if the notice cannot be written, nobody gains access either. */
    @Test
    void aShareWhoseNoticeFailsGrantsNothing() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION refuse_notices() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'notices are down'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_notices BEFORE INSERT ON share_notices FOR EACH ROW EXECUTE FUNCTION refuse_notices()""").update();
        try {
            assertThatThrownBy(() -> share("ravi", "d-roadmap", "user:kabir", "viewer")).hasRootCauseMessage("ERROR: notices are down\n  Where: PL/pgSQL function refuse_notices() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_notices ON share_notices; DROP FUNCTION refuse_notices()").update();
        }
        open("kabir", "d-roadmap").andExpect(status().isNotFound());
        assertThat(jdbc.sql("SELECT count(*) FROM relation_tuples WHERE subject_id = 'kabir'").query(Long.class).single()).isZero();
    }
}
