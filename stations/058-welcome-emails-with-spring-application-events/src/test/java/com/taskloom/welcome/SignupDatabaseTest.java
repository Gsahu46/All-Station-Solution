package com.taskloom.welcome;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The tables' rules with Java bypassed, and a sign-up rolled back whole. */
class SignupDatabaseTest extends ApiTest {

    @Test
    void namedConstraintsHoldWithoutJava() {
        jdbc.sql("INSERT INTO signups (email, name) VALUES ('asha@x.com', 'Asha')").update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO signups (email, name) VALUES ('ASHA@x.com', 'Asha')").update()).hasMessageContaining("signups_email_unique");
        assertThatThrownBy(() -> jdbc.sql("UPDATE invites SET seats_used = 4 WHERE code = 'OPS-FULL'").update()).hasMessageContaining("invites_seats_within_total");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO signups (email, name, invite_code) VALUES ('b@x.com', 'B', 'NOPE')").update()).hasMessageContaining("signups_invite_fk");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO sent_emails (signup_id, kind, status) VALUES (99, 'WELCOME', 'SENT')").update()).hasMessageContaining("sent_emails_signup_fk");
        long id = jdbc.sql("SELECT id FROM signups").query(Long.class).single();
        jdbc.sql("INSERT INTO sent_emails (signup_id, kind, status) VALUES (?, 'WELCOME', 'SENT')").param(id).update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO sent_emails (signup_id, kind, status) VALUES (?, 'WELCOME', 'SENT')").param(id).update()).hasMessageContaining("sent_emails_once");
        assertThatThrownBy(() -> jdbc.sql("UPDATE sent_emails SET status = 'DEAD'").update()).hasMessageContaining("sent_emails_dead_has_error");
        assertThatThrownBy(() -> jdbc.sql("UPDATE sent_emails SET status = 'LOST'").update()).hasMessageContaining("sent_emails_status_known");
    }

    @Test
    void aFullInviteRollsBackTheSignupItself() throws Exception {
        signUp("ravi@x.com", "Ravi Menon", "OPS-FULL").andExpect(status().isConflict());
        assertThat(jdbc.sql("SELECT count(*) FROM signups").query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT seats_used FROM invites WHERE code = 'OPS-FULL'").query(Integer.class).single()).isEqualTo(3);
        signUp("ravi@x.com", "Ravi Menon", null).andExpect(status().isCreated());   // the email is free again
    }
}
