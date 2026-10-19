package com.fitnest.workouts;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import tools.jackson.databind.JsonNode;

import javax.crypto.SecretKey;
import java.time.Duration;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. Two old designs: sessions kept in one server's memory (lost when the pod restarts), and the first
 * "JWT" fix that only base64-decoded the token to read who it was for. Then the same tokens against the real API.
 */
class UnverifiedTokenTrapTest extends ApiTest {

    @Autowired
    SecretKey jwtKey;

    /** The old fix: read the payload, trust it. No signature, no expiry, no issuer or audience. */
    static String oldReadSubject(String token) {
        JsonNode payload = JSON.readTree(new String(Base64.getUrlDecoder().decode(token.split("\\.")[1])));
        return payload.get("sub").asString();
    }

    @Test
    void sessionsInOnePodsMemoryAreLostWhenItRestarts() {
        Map<String, String> podMemory = new HashMap<>();   // the old login stored "session id -> member" here
        String session = UUID.randomUUID().toString();
        podMemory.put(session, "asha");
        Map<String, String> afterRestart = new HashMap<>();   // a restarted (or different) pod starts empty
        assertThat(afterRestart.get(session)).isNull();      // asha is logged out
    }

    @Test
    void aSignedTokenWorksOnAnyPodWithTheSameKey() throws Exception {
        String token = login("asha", "asha-demo-pass");
        // Another pod: a decoder built from the shared key, with nothing remembered about the login.
        NimbusJwtDecoder anotherPod = NimbusJwtDecoder.withSecretKey(jwtKey).macAlgorithm(MacAlgorithm.HS256).build();
        JwtTimestampValidator expiry = new JwtTimestampValidator();
        expiry.setClock(clock);   // the test clock, not the machine's
        anotherPod.setJwtValidator(expiry);
        assertThat(anotherPod.decode(token).getSubject()).isEqualTo("asha");
    }

    @Test
    void readingWithoutVerifyingTrustsAForgedToken() throws Exception {
        String forged = forge("someone-elses-key-that-is-at-least-256-bits".getBytes(), "ravi", "https://auth.fitnest.example", "fitnest-api", START.plusSeconds(900));
        assertThat(oldReadSubject(forged)).isEqualTo("ravi");   // the old code would show ravi's workouts
        workouts(forged).andExpect(status().isUnauthorized());
    }

    @Test
    void readingWithoutVerifyingTrustsAnUnsignedToken() throws Exception {
        String unsigned = b64("{\"alg\":\"none\"}") + "." + b64("{\"sub\":\"ravi\",\"iss\":\"https://auth.fitnest.example\",\"aud\":\"fitnest-api\",\"scope\":\"workouts:read\",\"exp\":9999999999}") + ".";
        assertThat(oldReadSubject(unsigned)).isEqualTo("ravi");
        workouts(unsigned).andExpect(status().isUnauthorized());
    }

    @Test
    void readingWithoutVerifyingTrustsAnExpiredToken() throws Exception {
        String token = login("asha", "asha-demo-pass");
        later(Duration.ofDays(30));
        assertThat(oldReadSubject(token)).isEqualTo("asha");   // a month later, still "asha" to the old code
        workouts(token).andExpect(status().isUnauthorized());
    }
}
