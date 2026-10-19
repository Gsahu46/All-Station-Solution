package com.fitnest.workouts;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: coach kabir (password "kabir-demo-pass", scope coach:read) reads GET /workouts/{member} for his
 * trainees only (demo rule: asha). Another member is 403; a member without coach:read is 403 even for themselves.
 */
class CoachReadsTraineesChallengeTest extends ApiTest {

    String token;

    @Test
    void aCoachReadsOnlyTheirOwnTrainees() throws Exception {
        token = login("kabir", "kabir-demo-pass");
        mvc.perform(get("/workouts/asha").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk()).andExpect(jsonPath("$.member").value("asha")).andExpect(jsonPath("$.workouts.length()").value(2));
        mvc.perform(get("/workouts/ravi").header("Authorization", "Bearer " + token)).andExpect(status().isForbidden());
    }

    @Test
    void aMemberIsNotACoach() throws Exception {
        token = login("ravi", "ravi-demo-pass");
        mvc.perform(get("/workouts/ravi").header("Authorization", "Bearer " + token)).andExpect(status().isForbidden());
        mvc.perform(get("/workouts/asha")).andExpect(status().isUnauthorized());
    }
}
