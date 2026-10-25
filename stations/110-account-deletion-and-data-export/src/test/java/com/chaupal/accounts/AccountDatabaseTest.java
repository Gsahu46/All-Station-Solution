package com.chaupal.accounts;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules hold for any writer, and an erasure is all or nothing. */
class AccountDatabaseTest extends ApiTest {

    @Test
    void theRulesAreNamedConstraintsInTheDatabase() {
        assertThatThrownBy(() -> jdbc.sql("UPDATE users SET status = 'DELETED', deleted_at = now() WHERE id = 2").update())
                .hasMessageContaining("users_deleted_holds_nothing");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO erasures (user_id, requested_at, due_by) VALUES (2, now(), now() + interval '120 days')").update())
                .hasMessageContaining("erasures_within_90_days");
        assertThatThrownBy(() -> jdbc.sql("UPDATE invoices SET retain_until = issued_on").update())
                .hasMessageContaining("invoices_retained_after_issue");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO data_exports (user_id, status) VALUES (2, 'READY')").update())
                .hasMessageContaining("data_exports_ready_has_content");
    }

    @Test
    void anErasureThatFailsHalfWayErasesNothing() {
        // Something new points at Imran's post and refuses to let it go: the erasure must stop, and undo what it did.
        jdbc.sql("CREATE TABLE post_reports (post_id BIGINT REFERENCES posts (id))").update();
        try {
            jdbc.sql("INSERT INTO post_reports VALUES (1)").update();
            accounts.requestDeletion(1);
            assertThatThrownBy(() -> accounts.erase(1)).hasMessageContaining("post_reports");
            assertThat(foundIn(IMRANS_DIGITS)).contains("otp_requests.phone", "users.phone");
            assertThat(jdbc.sql("SELECT count(*) FROM profiles WHERE user_id = 1").query(Integer.class).single()).isEqualTo(1);
        } finally {
            jdbc.sql("DROP TABLE post_reports").update();
        }
    }
}
