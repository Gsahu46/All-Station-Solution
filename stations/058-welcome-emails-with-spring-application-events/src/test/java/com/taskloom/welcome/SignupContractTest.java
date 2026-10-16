package com.taskloom.welcome;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: sign up, with or without an invite, and the welcome email that follows; valid, invalid, not found. */
class SignupContractTest extends ApiTest {

    @Test
    void aSignupIsAnsweredAtOnceAndWelcomedAfter() throws Exception {
        String url = signUp("Asha@X.com", "Asha Verma", null).andExpect(status().isCreated())
                .andExpect(content().json("{\"id\":1,\"email\":\"asha@x.com\",\"name\":\"Asha Verma\",\"welcomeEmail\":\"PENDING\"}"))
                .andReturn().getResponse().getHeader("Location");
        eventually(() -> assertThat(mailbox.all()).hasSize(1));
        MailGateway.Message m = mailbox.all().getFirst();
        assertThat(m.to()).isEqualTo("asha@x.com");
        assertThat(m.subject()).isEqualTo("Welcome to Taskloom, Asha Verma");
        assertThat(m.contentType()).isEqualTo("text/html; charset=UTF-8");
        eventually(() -> assertThat(welcomeStatus(1)).isEqualTo("SENT"));
        mvc.perform(get(url)).andExpect(jsonPath("$.welcomeEmail").value("SENT"));
    }

    @Test
    void theNameIsTextInTheEmailNotHtmlOrHeaders() throws Exception {
        signUp("zoe@x.com", "Zoë <b>& co</b>", null).andExpect(status().isCreated());
        eventually(() -> assertThat(mailbox.all()).hasSize(1));
        assertThat(mailbox.all().getFirst().html()).contains("Hi Zoë &lt;b&gt;&amp; co&lt;/b&gt;,").doesNotContain("<b>");
        mailbox.clear();
        signUp("bcc@x.com", "Eve\\r\\nBcc: everyone@x.com", null).andExpect(status().isCreated());
        eventually(() -> assertThat(mailbox.all()).hasSize(1));
        assertThat(mailbox.all().getFirst().subject()).isEqualTo("Welcome to Taskloom, Eve Bcc: everyone@x.com").doesNotContain("\n", "\r");
    }

    @Test
    void anInviteWithSeatsJoinsTheTeam() throws Exception {
        signUp("meera@x.com", "Meera Nair", "design-26").andExpect(status().isCreated());
        assertThat(jdbc.sql("SELECT seats_used FROM invites WHERE code = 'DESIGN-26'").query(Integer.class).single()).isEqualTo(1);
        eventually(() -> assertThat(mailbox.all()).hasSize(1));
    }

    @Test
    void aFullOrUnknownInviteOrATakenEmailIsRefusedAndNotWelcomed() throws Exception {
        signUp("ravi@x.com", "Ravi Menon", "OPS-FULL").andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Invite full"));
        signUp("ravi@x.com", "Ravi Menon", "NOPE-99").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Unknown invite"));
        signUp("asha@x.com", "Asha Verma", null).andExpect(status().isCreated());
        eventually(() -> assertThat(mailbox.all()).hasSize(1));
        signUp("ASHA@x.com", "Asha again", null).andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Already signed up"));
        Thread.sleep(300);
        assertThat(mailbox.all()).hasSize(1);   // one welcome, for the one real sign-up
    }

    @Test
    void malformedSignupsAre400() throws Exception {
        signUp("not-an-email", "Asha", null).andExpect(status().isBadRequest());
        signUp("asha@x.com", " ", null).andExpect(status().isBadRequest());
        signUp("asha@x.com", "Asha", "ab").andExpect(status().isBadRequest());
        mvc.perform(post("/signups").contentType(MediaType.APPLICATION_JSON).content("{\"name\":\"Asha\"}")).andExpect(status().isBadRequest());
        neverAnyMail();
    }

    @Test
    void unknownSignupsAre404() throws Exception {
        mvc.perform(get("/signups/99")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No sign-up 99."));
    }
}
