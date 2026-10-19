package com.fitnest.workouts;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.MACSigner;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.databind.json.JsonMapper;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.Date;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app with its security, a clock the tests move, and a known test signing key. Tokens can
 * be issued by the real login, or made by hand with Nimbus to play an attacker.
 */
@SpringBootTest(properties = "fitnest.jwt.secret=" + ApiTest.SECRET)
@AutoConfigureMockMvc
abstract class ApiTest {

    static final String SECRET = "dGVzdC1vbmx5LWZpdG5lc3Qtand0LXNlY3JldC1rZXktMjU2LWJpdHMtb3ItbW9yZQ";
    static final Instant START = Instant.parse("2026-10-19T06:00:00Z");
    static final JsonMapper JSON = JsonMapper.builder().build();

    static final class TestClock extends Clock {
        Instant now = START;

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return now;
        }
    }

    static final TestClock CLOCK = new TestClock();

    @TestBean
    Clock clock;

    static Clock clock() {
        return CLOCK;
    }

    @Autowired
    MockMvc mvc;

    @BeforeEach
    void resetClock() {
        CLOCK.now = START;
    }

    void later(Duration d) {
        CLOCK.now = CLOCK.now.plus(d);
    }

    ResultActions loginRequest(String username, String password) throws Exception {
        return mvc.perform(post("/auth/login").contentType(MediaType.APPLICATION_JSON)
                .content("{\"username\":\"%s\",\"password\":\"%s\"}".formatted(username, password)));
    }

    String login(String username, String password) throws Exception {
        return JSON.readTree(loginRequest(username, password).andReturn().getResponse().getContentAsString()).get("accessToken").asString();
    }

    ResultActions workouts(String token) throws Exception {
        return mvc.perform(get("/workouts/me").header("Authorization", "Bearer " + token));
    }

    /** A token made by hand: what an attacker can build. Claims follow the real ones unless the test changes them. */
    static String forge(byte[] key, String subject, String issuer, String audience, Instant expires) {
        try {
            JWTClaimsSet claims = new JWTClaimsSet.Builder().subject(subject).issuer(issuer).audience(audience)
                    .issueTime(Date.from(START)).expirationTime(Date.from(expires)).claim("scope", "workouts:read").build();
            SignedJWT jwt = new SignedJWT(new JWSHeader(JWSAlgorithm.HS256), claims);
            jwt.sign(new MACSigner(key));
            return jwt.serialize();
        } catch (JOSEException e) {
            throw new IllegalStateException(e);
        }
    }

    static byte[] realKey() {
        return Base64.getUrlDecoder().decode(SECRET);
    }

    static String b64(String json) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(json.getBytes());
    }
}
