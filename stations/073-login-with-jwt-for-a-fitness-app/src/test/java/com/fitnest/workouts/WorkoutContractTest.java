package com.fitnest.workouts;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class WorkoutContractTest extends ApiTest {

    @Test
    void loginGivesAShortLivedBearerToken() throws Exception {
        loginRequest("asha", "asha-demo-pass").andExpect(status().isOk())
                .andExpect(jsonPath("$.tokenType").value("Bearer")).andExpect(jsonPath("$.expiresIn").value(900))
                .andExpect(jsonPath("$.accessToken").value(org.hamcrest.Matchers.matchesPattern("[\\w-]+\\.[\\w-]+\\.[\\w-]+")));
    }

    /** The payload is readable by anyone who holds the token: only what the API needs, and the scope is the member's grants only. */
    @Test
    void thePayloadSaysWhoForWhichApiAndWhatTheyMayDo() throws Exception {
        String token = login("asha", "asha-demo-pass");
        tools.jackson.databind.JsonNode payload = JSON.readTree(java.util.Base64.getUrlDecoder().decode(token.split("\\.")[1]));
        org.assertj.core.api.Assertions.assertThat(payload.get("sub").asString()).isEqualTo("asha");
        org.assertj.core.api.Assertions.assertThat(payload.get("iss").asString()).isEqualTo("https://auth.fitnest.example");
        org.assertj.core.api.Assertions.assertThat(payload.get("scope").asString()).isEqualTo("workouts:read");   // Spring Security 7 also adds FACTOR_PASSWORD at sign-in
        org.assertj.core.api.Assertions.assertThat(payload.get("exp").asLong() - payload.get("iat").asLong()).isEqualTo(900);
    }

    @Test
    void theTokenOpensTheMembersOwnWorkouts() throws Exception {
        workouts(login("asha", "asha-demo-pass")).andExpect(status().isOk())
                .andExpect(jsonPath("$.member").value("asha")).andExpect(jsonPath("$.workouts[*].activity", contains("Run", "Yoga")));
        workouts(login("ravi", "ravi-demo-pass")).andExpect(jsonPath("$.workouts[*].activity", contains("Cycling")));
    }

    @Test
    void aMemberWithNoWorkoutsGetsAnEmptyList() throws Exception {
        workouts(login("meera", "meera-demo-pass")).andExpect(status().isOk()).andExpect(jsonPath("$.workouts", empty()));
    }

    @Test
    void aWrongPasswordOrAnUnknownMemberIs401AndAMalformedLoginIs400() throws Exception {
        loginRequest("asha", "not-her-password").andExpect(status().isUnauthorized()).andExpect(jsonPath("$.detail").value("Wrong username or password"));
        loginRequest("nobody", "any-password").andExpect(status().isUnauthorized()).andExpect(jsonPath("$.detail").value("Wrong username or password"));
        loginRequest("", "x").andExpect(status().isBadRequest());
        loginRequest("a".repeat(51), "x").andExpect(status().isBadRequest());
    }
}
