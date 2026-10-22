package com.streamo.config;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.context.bean.override.convention.TestBean;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: Last-Modified. Each answer says when its platform's config was published; an app that sends
 * If-Modified-Since with that date (and no If-None-Match) gets 304 until the next publish.
 */
class LastModifiedChallengeTest extends ApiTest {

    static volatile Instant now = Instant.parse("2026-10-22T10:00:00Z");

    @TestBean
    Clock clock;

    static Clock clock() {
        return new Clock() {
            public ZoneId getZone() {
                return ZoneOffset.UTC;
            }

            public Clock withZone(ZoneId zone) {
                return this;
            }

            public Instant instant() {
                return now;
            }
        };
    }

    MockHttpServletResponse since(String date) throws Exception {
        return mvc.perform(config("android", "6.1.0").header("If-Modified-Since", date)).andReturn().getResponse();
    }

    @Test
    void anUnchangedConfigIs304ByDateAndAPublishMakesIt200() throws Exception {
        now = Instant.parse("2026-10-22T10:00:00Z");
        configs.reset();   // published at 10:00 UTC
        MockHttpServletResponse first = mvc.perform(config("android", "6.1.0")).andReturn().getResponse();
        assertThat(first.getHeader("Last-Modified")).isEqualTo("Thu, 22 Oct 2026 10:00:00 GMT");
        assertThat(since("Thu, 22 Oct 2026 10:00:00 GMT").getStatus()).isEqualTo(304);
        now = Instant.parse("2026-10-22T11:30:00Z");
        configs.publish("android", configs.get("android"));   // republished at 11:30
        MockHttpServletResponse after = since("Thu, 22 Oct 2026 10:00:00 GMT");
        assertThat(after.getStatus()).isEqualTo(200);
        assertThat(after.getHeader("Last-Modified")).isEqualTo("Thu, 22 Oct 2026 11:30:00 GMT");
    }
}
