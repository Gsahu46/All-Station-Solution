package com.streamo.devices;

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

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app with its security on a real PostgreSQL, a test signing key, and a clock the tests move.
 * Before each test: the two demo members, no devices, no refresh tokens.
 */
@SpringBootTest(properties = "streamo.jwt.secret=" + ApiTest.SECRET)
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final String SECRET = "dGVzdC1vbmx5LXN0cmVhbW8tYWNjZXNzLXRva2VuLWtleS0yNTYtYml0cy1vci1tb3Jl";
    static final Instant START = Instant.parse("2026-10-19T06:00:00Z");
    static final JsonMapper JSON = JsonMapper.builder().build();

    static final class TestClock extends Clock {
        Instant now = START;
        Duration step = Duration.ZERO;   // how far each read moves the clock: a real clock never reads the same twice

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
            Instant t = now;
            now = now.plus(step);
            return t;
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
    void noDevices() {
        CLOCK.now = START;
        CLOCK.step = Duration.ZERO;
        jdbc.sql("DELETE FROM device_sessions").update();   // cascades to refresh_tokens
    }

    void later(Duration d) {
        CLOCK.now = CLOCK.now.plus(d);
    }

    ResultActions loginRequest(String email, String password, String deviceName, String deviceType) throws Exception {
        return mvc.perform(post("/auth/login").contentType(MediaType.APPLICATION_JSON).content(
                "{\"email\":\"%s\",\"password\":\"%s\",\"deviceName\":\"%s\",\"deviceType\":\"%s\"}".formatted(email, password, deviceName, deviceType)));
    }

    /** A sign-in that must work: the token pair as JSON. */
    JsonNode login(String member, String deviceName, String deviceType) throws Exception {
        return body(loginRequest(member + "@example.com", member + "-demo-pass", deviceName, deviceType));
    }

    ResultActions refreshRequest(String refreshToken) throws Exception {
        return mvc.perform(post("/auth/refresh").contentType(MediaType.APPLICATION_JSON).content("{\"refreshToken\":\"" + refreshToken + "\"}"));
    }

    ResultActions devices(String accessToken) throws Exception {
        return mvc.perform(get("/me/devices").header("Authorization", "Bearer " + accessToken));
    }

    ResultActions removeDevice(String accessToken, String deviceId) throws Exception {
        return mvc.perform(delete("/me/devices/{id}", deviceId).header("Authorization", "Bearer " + accessToken));
    }

    ResultActions logout(String accessToken) throws Exception {
        return mvc.perform(post("/auth/logout").header("Authorization", "Bearer " + accessToken));
    }

    static JsonNode body(ResultActions result) throws Exception {
        return JSON.readTree(result.andReturn().getResponse().getContentAsString());
    }

    static String access(JsonNode pair) {
        return pair.get("accessToken").asString();
    }

    static String refresh(JsonNode pair) {
        return pair.get("refreshToken").asString();
    }

    String revokedReason(String deviceId) {
        return jdbc.sql("SELECT revoked_reason FROM device_sessions WHERE id = ?::uuid").param(deviceId).query(String.class).list().getFirst();   // null while active
    }
}
