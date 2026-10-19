package com.hireloop.resets;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: PUT /candidates/me/password {currentPassword, newPassword} (signed in) changes the password: 204, 422
 * for a wrong current password. Like a reset, it cancels every open reset link of the account.
 */
class ChangePasswordCancelsLinksChallengeTest extends ApiTest {

    @Test
    void changingThePasswordKillsWaitingLinks() throws Exception {
        requestReset("arjun@example.com");
        String waiting = linkTokenFor("arjun@example.com");
        mvc.perform(put("/candidates/me/password").with(httpBasic("arjun@example.com", "arjun-old-password")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"currentPassword\":\"arjun-old-password\",\"newPassword\":\"arjun-new-long-password\"}")).andExpect(status().isNoContent());
        complete(waiting, "attacker-chosen-password").andExpect(status().isBadRequest());
        me("arjun@example.com", "arjun-new-long-password").andExpect(status().isOk());
    }

    @Test
    void theCurrentPasswordMustBeRight() throws Exception {
        mvc.perform(put("/candidates/me/password").with(httpBasic("arjun@example.com", "arjun-old-password")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"currentPassword\":\"a-wrong-password\",\"newPassword\":\"arjun-new-long-password\"}")).andExpect(status().isUnprocessableContent());
    }
}
