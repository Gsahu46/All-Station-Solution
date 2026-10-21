package com.taskloom.board;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The rules hold for every writer, not only this app: plain SQL straight to PostgreSQL, no Java checks on the way. */
class TaskDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining(constraint);
    }

    @Test
    void anUpdateThatForgetsTheVersionIsRefused() {
        // The old last-write-wins code, run straight against the database.
        violates("tasks_version_must_increase", "UPDATE tasks SET status = 'done' WHERE id = 1");
        violates("tasks_version_must_increase", "UPDATE tasks SET status = 'done', version = 7 WHERE id = 1");
        jdbc.sql("UPDATE tasks SET status = 'done', version = version + 1 WHERE id = 1 AND version = 0").update();
        assertThat(jdbc.sql("SELECT version FROM tasks WHERE id = 1").query(Long.class).single()).isEqualTo(1);
    }

    @Test
    void taskRulesHoldWithoutJava() {
        violates("tasks_status", "UPDATE tasks SET status = 'blocked', version = version + 1 WHERE id = 1");
        violates("tasks_title_length", "UPDATE tasks SET title = '', version = version + 1 WHERE id = 1");
        violates("tasks_board_title_unique", "INSERT INTO tasks (board, title, description, status) VALUES ('launch', 'Book the venue', '', 'open')");
        violates("tasks_version_nonnegative", "INSERT INTO tasks (board, title, description, status, version) VALUES ('launch', 'New', '', 'open', -1)");
        violates("task_changes_one_per_version", "INSERT INTO task_changes (task_id, version, title, status) VALUES (1, 1, 'a', 'open'), (1, 1, 'b', 'open')");
    }

    /** The change and its activity row are one transaction: if the feed cannot be written, the task does not change. */
    @Test
    void anEditWhoseActivityRowFailsLeavesTheTaskAsItWas() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION refuse_changes() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'feed is down'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_changes BEFORE INSERT ON task_changes FOR EACH ROW EXECUTE FUNCTION refuse_changes()""").update();
        try {
            assertThatThrownBy(() -> edit(1, "\"0\"", body("Write the press release", "done", "asha"))).hasRootCauseMessage("ERROR: feed is down\n  Where: PL/pgSQL function refuse_changes() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_changes ON task_changes; DROP FUNCTION refuse_changes()").update();
        }
        read(1).andExpect(header().string("ETag", "\"0\""));
        edit(1, "\"0\"", body("Write the press release", "done", "asha")).andExpect(status().isOk());   // the same edit, now accepted
    }
}
