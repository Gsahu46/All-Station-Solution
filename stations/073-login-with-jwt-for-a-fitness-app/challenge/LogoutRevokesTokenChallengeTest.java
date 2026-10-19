package com.fitnest.workouts;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /auth/logout with the token makes that one token stop working at once (204), on every pod
 * that shares the revoked list, while a fresh login still works. A revoked id only needs keeping until the token
 * would have expired anyway.
 */
class LogoutRevokesTokenChallengeTest extends ApiTest {

    @Test
    void aLoggedOutTokenIsRefusedButANewLoginWorks() throws Exception {
        String token = login("asha", "asha-demo-pass");
        workouts(token).andExpect(status().isOk());
        mvc.perform(post("/auth/logout").header("Authorization", "Bearer " + token)).andExpect(status().isNoContent());
        workouts(token).andExpect(status().isUnauthorized());
        later(Duration.ofSeconds(1));
        workouts(login("asha", "asha-demo-pass")).andExpect(status().isOk());
    }

    @Test
    void logoutNeedsAValidToken() throws Exception {
        mvc.perform(post("/auth/logout")).andExpect(status().isUnauthorized());
    }
}
