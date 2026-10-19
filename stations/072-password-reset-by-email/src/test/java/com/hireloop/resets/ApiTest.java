package com.hireloop.resets;

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

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app with security on a real PostgreSQL, a clock the tests can move forward, and before each
 * test the three demo candidates with their original passwords, no reset links and an empty outbox.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    /** A clock that stands still until a test moves it. */
    static final class TestClock extends Clock {
        Instant now = Instant.parse("2026-10-19T06:00:00Z");

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
    void demoData() {
        CLOCK.now = Instant.parse("2026-10-19T06:00:00Z");
        jdbc.sql("DELETE FROM outbox_emails").update();
        jdbc.sql("DELETE FROM candidates").update();   // cascades to password_resets
        jdbc.sql("""
                INSERT INTO candidates (email, full_name, password_hash, status) VALUES
                    ('priya@example.com', 'Priya Nair', '{bcrypt}' || crypt('priya-old-password', gen_salt('bf', 10)), 'ACTIVE'),
                    ('arjun@example.com', 'Arjun Mehta', '{bcrypt}' || crypt('arjun-old-password', gen_salt('bf', 10)), 'ACTIVE'),
                    ('kiran@example.com', 'Kiran Das', '{bcrypt}' || crypt('kiran-old-password', gen_salt('bf', 10)), 'SUSPENDED')""").update();
    }

    void later(Duration duration) {
        CLOCK.now = CLOCK.now.plus(duration);
    }

    ResultActions requestReset(String email) throws Exception {
        return mvc.perform(post("/password-resets").contentType(MediaType.APPLICATION_JSON).content("{\"email\":\"" + email + "\"}"));
    }

    ResultActions complete(String token, String newPassword) throws Exception {
        return mvc.perform(post("/password-resets/{token}/complete", token).contentType(MediaType.APPLICATION_JSON)
                .content("{\"newPassword\":\"" + newPassword + "\"}"));
    }

    ResultActions me(String email, String password) throws Exception {
        return mvc.perform(get("/candidates/me").with(httpBasic(email, password)));
    }

    long emailsTo(String email) {
        return jdbc.sql("SELECT count(*) FROM outbox_emails WHERE to_email = ?").param(email).query(Long.class).single();
    }

    /** The token from the newest email to this address, as the person would click it. */
    String linkTokenFor(String email) {
        String body = jdbc.sql("SELECT body FROM outbox_emails WHERE to_email = ? ORDER BY id DESC LIMIT 1").param(email).query(String.class).single();
        Matcher m = Pattern.compile("token=([A-Za-z0-9_-]+)").matcher(body);
        if (!m.find()) {
            throw new AssertionError("no link in " + body);
        }
        return m.group(1);
    }
}
