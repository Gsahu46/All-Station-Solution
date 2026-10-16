package com.taskloom.welcome;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: a third after-commit listener records every committed sign-up in analytics_events (a new migration),
 * without a line changed in SignupService. A rolled-back sign-up records nothing.
 */
class AnalyticsChallengeTest extends ApiTest {

    long analytics() {
        return jdbc.sql("SELECT count(*) FROM analytics_events WHERE name = 'signed_up'").query(Long.class).single();
    }

    @Test
    void onlyCommittedSignupsAreCounted() throws Exception {
        jdbc.sql("DELETE FROM analytics_events").update();
        signUp("asha@x.com", "Asha Verma", null).andExpect(status().isCreated());
        signUp("ravi@x.com", "Ravi Menon", "OPS-FULL").andExpect(status().isConflict());
        eventually(() -> assertThat(analytics()).isEqualTo(1));
        Thread.sleep(300);
        assertThat(analytics()).isEqualTo(1);
    }
}
