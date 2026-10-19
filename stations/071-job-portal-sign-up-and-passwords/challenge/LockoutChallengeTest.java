package com.hireloop.candidates;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: after 5 wrong passwords in a row an account is locked for 15 minutes: even the right password gets
 * the same 401 as before, so the lock reveals nothing. A successful sign-in resets the count.
 */
class LockoutChallengeTest extends ApiTest {

    @Test
    void fiveWrongPasswordsLockTheAccount() throws Exception {
        for (int i = 0; i < 5; i++) {
            me("arjun@example.com", "guess-number-" + i).andExpect(status().isUnauthorized());
        }
        me("arjun@example.com", "Hireloop@123").andExpect(status().isUnauthorized());
        assertThat(jdbc.sql("SELECT locked_until > now() FROM candidates WHERE email = 'arjun@example.com'").query(Boolean.class).single()).isTrue();
    }

    @Test
    void aSuccessfulSignInResetsTheCount() throws Exception {
        for (int i = 0; i < 4; i++) {
            me("priya@example.com", "guess-number-" + i).andExpect(status().isUnauthorized());
        }
        me("priya@example.com", "summer2024!").andExpect(status().isOk());
        for (int i = 0; i < 4; i++) {
            me("priya@example.com", "guess-again-" + i).andExpect(status().isUnauthorized());
        }
        me("priya@example.com", "summer2024!").andExpect(status().isOk());
    }
}
