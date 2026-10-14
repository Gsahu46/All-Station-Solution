package com.tijori.otp;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: an Idempotency-Key is remembered for 24 hours, then forgotten. A key seen again after that is a new
 * request (and the memory it used is freed).
 */
class KeyExpiryChallengeTest extends ApiTest {

    String requestId(String key) throws Exception {
        return JsonPath.read(otp(key, "9876543210").andReturn().getResponse().getContentAsString(), "$.requestId");
    }

    @Test
    void aKeyIsRememberedForADayThenForgotten() throws Exception {
        String first = requestId("old-key-123456");
        clock.advance(Duration.ofHours(23));
        assertThat(requestId("old-key-123456")).isEqualTo(first);
        clock.advance(Duration.ofHours(2));
        assertThat(requestId("old-key-123456")).isNotEqualTo(first);
        assertThat(sms.sentTo("9876543210")).isEqualTo(2);
    }
}
