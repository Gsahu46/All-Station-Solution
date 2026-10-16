package com.taskloom.welcome;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: Ravi signs up with a full team invite, the old way and the new way. */
@Import({OldSignupFlow.class, OldSignupFlow.OldWelcomeListener.class})
class EmailBeforeCommitTrapTest extends ApiTest {

    @Autowired
    OldSignupFlow old;

    long signups() {
        return jdbc.sql("SELECT count(*) FROM signups").query(Long.class).single();
    }

    @Test
    void aPlainListenerSendsBeforeTheRollback() {
        assertThatThrownBy(() -> old.signUp("ravi@x.com", "Ravi Menon", "OPS-FULL")).hasMessage("invite full");
        assertThat(signups()).isZero();                                                // no account...
        assertThat(mailbox.all()).extracting(MailGateway.Message::to).containsExactly("ravi@x.com");   // ...but "welcome!"
    }

    @Test
    void anAfterCommitListenerSendsNothingForARolledBackSignup() throws Exception {
        signUp("ravi@x.com", "Ravi Menon", "OPS-FULL").andExpect(status().isConflict());
        assertThat(signups()).isZero();
        neverAnyMail();
    }
}
