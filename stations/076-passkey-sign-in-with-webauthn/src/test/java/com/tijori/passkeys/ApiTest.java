package com.tijori.passkeys;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Shared setup: the whole app on a real PostgreSQL, a test signing key, a clock the tests move, and before each test
 * the two demo customers with no passkeys, no challenges and no used codes.
 */
@SpringBootTest(properties = "tijori.jwt.secret=" + ApiTest.SECRET)
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final String SECRET = "dGVzdC1vbmx5LXRpam9yaS1hY2Nlc3MtdG9rZW4ta2V5LTI1Ni1iaXRzLW9yLW1vcmU";
    static final byte[] TOTP_SECRET = "12345678901234567890".getBytes(StandardCharsets.US_ASCII);   // RFC 6238's test secret, as in V2
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
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void cleanSlate() {
        CLOCK.now = START;
        jdbc.sql("DELETE FROM passkeys").update();
        jdbc.sql("DELETE FROM webauthn_challenges").update();
        jdbc.sql("UPDATE customers SET totp_last_step = NULL").update();
    }

    void later(Duration d) {
        CLOCK.now = CLOCK.now.plus(d);
    }

    /** The code the customer's authenticator app shows right now. */
    static String currentCode() {
        return Totp.code(TOTP_SECRET, Totp.step(CLOCK.now.getEpochSecond()));
    }

    ResultActions codeSignIn(String email, String password, String code) throws Exception {
        return mvc.perform(post("/2fa/totp").contentType(MediaType.APPLICATION_JSON)
                .content("{\"email\":\"%s\",\"password\":\"%s\",\"code\":\"%s\"}".formatted(email, password, code)));
    }

    /** A sign-in with password and code that must work; then the clock moves past that code's 30 seconds. */
    String codeToken(String member) throws Exception {
        String token = body(codeSignIn(member + "@example.com", member + "-demo-pass", currentCode()).andExpect(status().isOk())).get("accessToken").asString();
        later(Duration.ofSeconds(30));
        return token;
    }

    ResultActions send(String path, String token, String json) throws Exception {
        var request = org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post(path).contentType(MediaType.APPLICATION_JSON).content(json);
        return mvc.perform(token == null ? request : request.header("Authorization", "Bearer " + token));
    }

    JsonNode registrationOptions(String token) throws Exception {
        return body(send("/webauthn/registration/options", token, "{}").andExpect(status().isOk()));
    }

    ResultActions register(String token, String label, ObjectNode credential) throws Exception {
        ObjectNode body = JSON.createObjectNode().put("label", label);
        body.set("credential", credential);
        return send("/webauthn/registration", token, body.toString());
    }

    /** A passkey on this device for this customer, through the real registration. */
    Device passkeyFor(String member) throws Exception {
        return passkeyOn(new Device(), member);
    }

    Device passkeyOn(Device phone, String member) throws Exception {
        String token = codeToken(member);
        register(token, member + "'s phone", phone.create(registrationOptions(token))).andExpect(status().isCreated());
        return phone;
    }

    JsonNode authenticationOptions() throws Exception {
        return body(send("/webauthn/authentication/options", null, "{}").andExpect(status().isOk()));
    }

    ResultActions authenticate(ObjectNode assertion) throws Exception {
        return send("/webauthn/authentication", null, assertion.toString());
    }

    ResultActions me(String token) throws Exception {
        return mvc.perform(get("/accounts/me").header("Authorization", "Bearer " + token));
    }

    static JsonNode body(ResultActions result) throws Exception {
        return JSON.readTree(result.andReturn().getResponse().getContentAsString());
    }
}
