package com.hireloop.resets;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: after a reset, a second email tells the owner "Your Hireloop password was changed", so someone who
 * did not ask for it notices at once. The notice contains no link.
 */
class ChangedNoticeChallengeTest extends ApiTest {

    @Test
    void theOwnerIsToldTheirPasswordChanged() throws Exception {
        requestReset("priya@example.com");
        complete(linkTokenFor("priya@example.com"), "priya-new-long-password");
        assertThat(jdbc.sql("SELECT subject FROM outbox_emails WHERE to_email = 'priya@example.com' ORDER BY id").query(String.class).list())
                .containsExactly("Reset your Hireloop password", "Your Hireloop password was changed");
        assertThat(jdbc.sql("SELECT body FROM outbox_emails WHERE subject = 'Your Hireloop password was changed'").query(String.class).single())
                .doesNotContain("token=");
    }
}
