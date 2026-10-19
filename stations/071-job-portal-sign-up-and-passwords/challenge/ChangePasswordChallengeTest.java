package com.hireloop.candidates;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: PUT /candidates/me/password {currentPassword, newPassword} changes the signed-in candidate's password:
 * 204. The current password must be given again (422 if wrong), and the new one follows the sign-up rules (400).
 */
class ChangePasswordChallengeTest extends ApiTest {

    private org.springframework.test.web.servlet.ResultActions change(String signedInWith, String current, String next) throws Exception {
        return mvc.perform(put("/candidates/me/password").with(httpBasic("arjun@example.com", signedInWith)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"currentPassword\":\"%s\",\"newPassword\":\"%s\"}".formatted(current, next)));
    }

    @Test
    void theOldPasswordStopsWorking() throws Exception {
        change("Hireloop@123", "Hireloop@123", "a-much-longer-passphrase").andExpect(status().isNoContent());
        me("arjun@example.com", "Hireloop@123").andExpect(status().isUnauthorized());
        me("arjun@example.com", "a-much-longer-passphrase").andExpect(status().isOk());
    }

    @Test
    void theCurrentPasswordIsCheckedAndTheNewOneFollowsTheRules() throws Exception {
        change("Hireloop@123", "not-my-password", "a-much-longer-passphrase").andExpect(status().isUnprocessableContent());
        change("Hireloop@123", "Hireloop@123", "short").andExpect(status().isBadRequest());
    }
}
