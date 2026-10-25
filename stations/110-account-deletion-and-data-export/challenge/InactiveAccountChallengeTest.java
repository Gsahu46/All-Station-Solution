package com.chaupal.accounts;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: accounts nobody has used for three years are erased, after a notice 48 hours before. Accounts.sweepInactive()
 * sends the notice once, and books the erasure when the 48 hours have passed with no sign-in.
 */
class InactiveAccountChallengeTest extends ApiTest {

    String status(long user) {
        return jdbc.sql("SELECT status FROM users WHERE id = ?").param(user).query(String.class).single();
    }

    int notices(String phone) {
        return jdbc.sql("SELECT count(*) FROM notification_outbox WHERE phone = ? AND text LIKE '%48 hours%'").param(phone).query(Integer.class).single();
    }

    @Test
    void threeQuietYearsANoticeThen48HoursThenErasure() {
        jdbc.sql("INSERT INTO login_events (user_id, ip, at) VALUES (2, '198.51.100.7', now() - interval '3 years 1 day')").update();
        accounts.sweepInactive();
        accounts.sweepInactive();
        assertThat(notices("+919822233344")).as("one notice, not one per sweep").isEqualTo(1);
        assertThat(status(2)).isEqualTo("ACTIVE");

        jdbc.sql("UPDATE users SET inactivity_notice_at = now() - interval '49 hours' WHERE id = 2").update();
        accounts.sweepInactive();
        assertThat(status(2)).isIn("DELETION_REQUESTED", "DELETED");
    }

    @Test
    void signingInAfterTheNoticeKeepsTheAccount() {
        jdbc.sql("INSERT INTO login_events (user_id, ip, at) VALUES (2, '198.51.100.7', now() - interval '3 years 1 day')").update();
        accounts.sweepInactive();
        jdbc.sql("UPDATE users SET inactivity_notice_at = now() - interval '49 hours' WHERE id = 2").update();
        jdbc.sql("INSERT INTO login_events (user_id, ip, at) VALUES (2, '198.51.100.7', now() - interval '1 hour')").update();
        accounts.sweepInactive();
        assertThat(status(2)).isEqualTo("ACTIVE");
        assertThat(status(1)).as("Imran signed in 2 days ago").isEqualTo("ACTIVE");
    }
}
