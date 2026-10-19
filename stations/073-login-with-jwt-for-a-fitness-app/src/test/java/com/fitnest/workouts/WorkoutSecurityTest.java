package com.fitnest.workouts;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.Base64;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Security: 401 for every kind of bad token, 403 for a missing scope, one member never another, and odd input. */
class WorkoutSecurityTest extends ApiTest {

    @Test
    void noTokenIs401WithABearerChallenge() throws Exception {
        mvc.perform(get("/workouts/me")).andExpect(status().isUnauthorized()).andExpect(header().string("WWW-Authenticate", "Bearer"));
    }

    @Test
    void aTokenExpiresAfter15MinutesWithOneMinuteForClockDifferences() throws Exception {
        String token = login("asha", "asha-demo-pass");
        later(Duration.ofMinutes(15).plusSeconds(30));
        workouts(token).andExpect(status().isOk());   // inside the 60-second allowance
        later(Duration.ofSeconds(31));
        workouts(token).andExpect(status().isUnauthorized());
    }

    @Test
    void aTokenFromAnotherIssuerOrForAnotherApiIs401() throws Exception {
        workouts(forge(realKey(), "asha", "https://evil.example", "fitnest-api", START.plusSeconds(900))).andExpect(status().isUnauthorized());
        workouts(forge(realKey(), "asha", "https://auth.fitnest.example", "fitnest-admin", START.plusSeconds(900))).andExpect(status().isUnauthorized());
        workouts(forge(realKey(), "asha", "https://auth.fitnest.example", "fitnest-api", START.plusSeconds(900))).andExpect(status().isOk());   // the control: all claims right
    }

    @Test
    void aMemberWithoutTheScopeIs403() throws Exception {
        workouts(login("newbie", "newbie-demo-pass")).andExpect(status().isForbidden()).andExpect(jsonPath("$.title").value("Not allowed"));
    }

    @Test
    void changingWhoTheTokenIsForBreaksItsSignature() throws Exception {
        String[] parts = login("asha", "asha-demo-pass").split("\\.");
        String payload = new String(Base64.getUrlDecoder().decode(parts[1])).replace("\"sub\":\"asha\"", "\"sub\":\"ravi\"");
        workouts(parts[0] + "." + b64(payload) + "." + parts[2]).andExpect(status().isUnauthorized());
        // And nothing in the request chooses the member: a query parameter is ignored.
        mvc.perform(get("/workouts/me").param("member", "ravi").header("Authorization", "Bearer " + login("asha", "asha-demo-pass")))
                .andExpect(jsonPath("$.workouts[*].activity", contains("Run", "Yoga")));
    }

    @Test
    void garbageInTheHeaderIs401NotAnError() throws Exception {
        for (String header : new String[]{"Bearer not.a.jwt", "Bearer ' OR '1'='1", "Bearer " + "a".repeat(5000), "Basic YXNoYTphc2hhLWRlbW8tcGFzcw=="}) {
            mvc.perform(get("/workouts/me").header("Authorization", header)).andExpect(status().isUnauthorized());
        }
    }
}
