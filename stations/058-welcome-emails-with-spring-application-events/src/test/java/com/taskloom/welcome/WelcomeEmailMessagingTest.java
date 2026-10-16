package com.taskloom.welcome;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doCallRealMethod;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Delivery of the welcome email: the same event twice, a provider that fails and recovers, and one that never does. */
class WelcomeEmailMessagingTest extends ApiTest {

    @MockitoSpyBean
    Mailbox provider;
    @Autowired
    WelcomeMailer mailer;

    SignedUp aSignup() {
        long id = jdbc.sql("INSERT INTO signups (email, name) VALUES ('asha@x.com', 'Asha Verma') RETURNING id").query(Long.class).single();
        return new SignedUp(id, "asha@x.com", "Asha Verma");
    }

    String row(long id) {
        return jdbc.sql("SELECT status || ' ' || attempts || coalesce(' ' || last_error, '') FROM sent_emails WHERE signup_id = ?").param(id).query(String.class).single();
    }

    @Test
    void theSameEventDeliveredFiveTimesAtOnceSendsOneEmail() throws Exception {
        SignedUp e = aSignup();
        together(5, () -> {
            mailer.sendOnce(e);
            return null;
        });
        assertThat(mailbox.all()).hasSize(1);
        assertThat(row(e.signupId())).isEqualTo("SENT 1");
    }

    @Test
    void aProviderThatFailsTwiceIsRetriedAndTheEmailGoesOnce() {
        doThrow(new IllegalStateException("421 try again later")).doThrow(new IllegalStateException("421 try again later"))
                .doCallRealMethod().when(provider).send(any());
        SignedUp e = aSignup();
        mailer.sendOnce(e);
        assertThat(mailbox.all()).hasSize(1);
        assertThat(row(e.signupId())).isEqualTo("SENT 3 421 try again later");
    }

    @Test
    void aProviderThatNeverRecoversLeavesTheEmailDeadForAPerson() throws Exception {
        doThrow(new IllegalStateException("550 mailbox unavailable")).when(provider).send(any());
        SignedUp e = aSignup();
        mailer.sendOnce(e);
        assertThat(mailbox.all()).isEmpty();
        assertThat(row(e.signupId())).isEqualTo("DEAD 3 550 mailbox unavailable");
        mvc.perform(get("/signups/{id}", e.signupId())).andExpect(jsonPath("$.welcomeEmail").value("DEAD"));

        doCallRealMethod().when(provider).send(any());
        mailer.sendOnce(e);   // a late duplicate of the same event does not resend a dead-lettered email
        assertThat(mailbox.all()).isEmpty();
        assertThat(List.of(row(e.signupId()))).containsExactly("DEAD 3 550 mailbox unavailable");
    }
}
