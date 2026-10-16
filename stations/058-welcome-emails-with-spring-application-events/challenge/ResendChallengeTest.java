package com.taskloom.welcome;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doCallRealMethod;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /signups/{id}/welcome-email/retry takes a DEAD email out of the dead-letter state and tries again,
 * with the same retries, answering the sign-up with its new status. Not DEAD: 409. Unknown sign-up: 404.
 */
class ResendChallengeTest extends ApiTest {

    @MockitoSpyBean
    Mailbox provider;

    @Test
    void aPersonCanSendADeadEmailAgain() throws Exception {
        doThrow(new IllegalStateException("550 mailbox unavailable")).when(provider).send(any());
        signUp("asha@x.com", "Asha Verma", null).andExpect(status().isCreated());
        eventually(() -> assertThat(welcomeStatus(1)).isEqualTo("DEAD"));

        doCallRealMethod().when(provider).send(any());   // the provider is back
        mvc.perform(post("/signups/1/welcome-email/retry")).andExpect(status().isOk()).andExpect(jsonPath("$.welcomeEmail").value("SENT"));
        assertThat(mailbox.all()).hasSize(1);
        mvc.perform(post("/signups/1/welcome-email/retry")).andExpect(status().isConflict());
        mvc.perform(post("/signups/99/welcome-email/retry")).andExpect(status().isNotFound());
    }
}
