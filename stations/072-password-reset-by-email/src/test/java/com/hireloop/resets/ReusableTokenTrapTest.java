package com.hireloop.resets;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old reset, kept here as plain SQL: a token stored as text, with no expiry and no "used" mark,
 * and a request form that said whether the email had an account. Then the same steps against the new endpoints.
 */
class ReusableTokenTrapTest extends ApiTest {

    @BeforeEach
    void oldTable() {
        jdbc.sql("CREATE TABLE old_reset_tokens (email VARCHAR(254), token VARCHAR(36))").update();
    }

    @AfterEach
    void dropOldTable() {
        jdbc.sql("DROP TABLE old_reset_tokens").update();
    }

    /** The old form's reply. */
    private String oldRequest(String email) {
        boolean exists = jdbc.sql("SELECT count(*) FROM candidates WHERE email = ?").param(email).query(Long.class).single() > 0;
        if (!exists) {
            return "No account found with this email";
        }
        jdbc.sql("INSERT INTO old_reset_tokens VALUES (?, ?)").params(email, UUID.randomUUID().toString()).update();
        return "We have sent you a reset link";
    }

    /** The old link check: does this token exist? Nothing else. */
    private boolean oldTokenWorks(String token) {
        return jdbc.sql("SELECT count(*) FROM old_reset_tokens WHERE token = ?").param(token).query(Long.class).single() > 0;
    }

    @Test
    void theOldFormToldAttackersWhichEmailsHaveAccounts() throws Exception {
        assertThat(oldRequest("priya@example.com")).isNotEqualTo(oldRequest("nobody@example.com"));
        String known = requestReset("priya@example.com").andReturn().getResponse().getContentAsString();
        String unknown = requestReset("nobody@example.com").andReturn().getResponse().getContentAsString();
        assertThat(known).isEqualTo(unknown);
    }

    @Test
    void anOldLinkWorkedTwiceAndForever() throws Exception {
        oldRequest("priya@example.com");
        String token = jdbc.sql("SELECT token FROM old_reset_tokens").query(String.class).single();   // and anyone reading the table can use it
        assertThat(oldTokenWorks(token)).isTrue();
        later(Duration.ofDays(31));
        assertThat(oldTokenWorks(token)).isTrue();   // a month later, still a key to the account
    }

    @Test
    void aNewLinkWorksOnceAndOnlyFor30Minutes() throws Exception {
        requestReset("priya@example.com");
        String token = linkTokenFor("priya@example.com");
        complete(token, "first-new-password").andExpect(status().isNoContent());
        complete(token, "second-new-password").andExpect(status().isBadRequest());   // used: the same answer as unknown

        requestReset("arjun@example.com");
        later(Duration.ofMinutes(31));
        complete(linkTokenFor("arjun@example.com"), "too-late-password").andExpect(status().isBadRequest());
        me("arjun@example.com", "arjun-old-password").andExpect(status().isOk());
    }

    @Test
    void theTableHoldsOnlyAHashOfTheLink() throws Exception {
        requestReset("priya@example.com");
        String token = linkTokenFor("priya@example.com");
        assertThat(jdbc.sql("SELECT count(*) FROM password_resets WHERE token_hash = ?").param(token).query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT token_hash FROM password_resets").query(String.class).single()).isEqualTo(PasswordResets.sha256(token));
    }
}
