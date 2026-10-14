package com.tijori.otp;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.concurrent.atomic.AtomicReference;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, a clock the tests move by hand, and nothing remembered between tests. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(ApiTest.TestClockConfig.class)
abstract class ApiTest {

    static final Instant START = Instant.parse("2026-10-14T09:00:00Z");

    /** A clock that only moves when a test says so. */
    static final class TestClock extends Clock {
        private final AtomicReference<Instant> now = new AtomicReference<>(START);

        void reset() {
            now.set(START);
        }

        void advance(Duration d) {
            now.updateAndGet(t -> t.plus(d));
        }

        @Override
        public Instant instant() {
            return now.get();
        }

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }
    }

    @TestConfiguration
    static class TestClockConfig {
        @Bean
        @Primary
        TestClock testClock() {
            return new TestClock();
        }
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    TestClock clock;
    @Autowired
    OtpLimiter limiter;
    @Autowired
    OtpService service;
    @Autowired
    SimulatedSmsSender sms;

    @BeforeEach
    void freshStart() {
        clock.reset();
        limiter.clear();
        service.clear();
        sms.clear();
    }

    ResultActions otp(String key, String mobile) throws Exception {
        return mvc.perform(post("/otp-requests").header("Idempotency-Key", key)
                .contentType(MediaType.APPLICATION_JSON).content("{\"mobile\":\"" + mobile + "\"}"));
    }
}
