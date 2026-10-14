package com.tijori.otp;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.time.Duration;

import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: an accepted request, the limit with Retry-After, the window moving, and every refusal. */
class OtpContractTest extends ApiTest {

    @Test
    void anOtpRequestIsAcceptedWithoutShowingTheCodeOrTheNumber() throws Exception {
        otp("first-tap-0001", "9876543210")
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.requestId").value(matchesPattern("otp_[0-9a-f]{32}")))
                .andExpect(jsonPath("$.mobile").value("XXXXXX3210"))
                .andExpect(jsonPath("$.expiresAt").value("2026-10-14T09:05:00Z"))
                .andExpect(jsonPath("$.attemptsLeft").value(2))
                .andExpect(jsonPath("$.code").doesNotExist());
    }

    @Test
    void theFourthIn10MinutesIs429WithRetryAfterFromTheOldest() throws Exception {
        otp("tap-a-000001", "9876543210");
        clock.advance(Duration.ofMinutes(1));
        otp("tap-b-000002", "+91 98765-43210");   // the same number: counts
        otp("tap-c-000003", "09876543210").andExpect(jsonPath("$.attemptsLeft").value(0));
        clock.advance(Duration.ofMinutes(3));
        otp("tap-d-000004", "9876543210")
                .andExpect(status().isTooManyRequests())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(header().string("Retry-After", "360"))   // the first one leaves the window at 09:10, 6 minutes away
                .andExpect(jsonPath("$.detail").value("This number has had 3 OTPs in the last 10 minutes. Try again in 360 seconds."));
        clock.advance(Duration.ofMinutes(6));
        otp("tap-e-000005", "9876543210").andExpect(status().isAccepted()).andExpect(jsonPath("$.attemptsLeft").value(0));
    }

    @Test
    void retryAfterCountsFromTheOldestRequestInTheWindow() throws Exception {
        otp("slot-1-000001", "9123456780");   // 09:00
        clock.advance(Duration.ofMinutes(2));
        otp("slot-2-000002", "9123456780");   // 09:02
        clock.advance(Duration.ofMinutes(2));
        otp("slot-3-000003", "9123456780");   // 09:04
        clock.advance(Duration.ofMinutes(1));  // 09:05: the 09:00 request frees its slot at 09:10
        otp("slot-4-000004", "9123456780").andExpect(status().isTooManyRequests()).andExpect(header().string("Retry-After", "300"));
        clock.advance(Duration.ofSeconds(299));
        otp("slot-5-000005", "9123456780").andExpect(status().isTooManyRequests()).andExpect(header().string("Retry-After", "1"));
        clock.advance(Duration.ofSeconds(1));
        otp("slot-6-000006", "9123456780").andExpect(status().isAccepted());
    }

    @Test
    void badRequestsAre400() throws Exception {
        otp("valid-key-01", "12345").andExpect(status().isBadRequest()).andExpect(jsonPath("$.title").value("Invalid mobile number"));
        otp("valid-key-02", "5876543210").andExpect(status().isBadRequest());
        otp("short", "9876543210").andExpect(status().isBadRequest());
        otp("bad key with spaces", "9876543210").andExpect(status().isBadRequest());
        mvc.perform(post("/otp-requests").contentType(MediaType.APPLICATION_JSON).content("{\"mobile\":\"9876543210\"}"))
                .andExpect(status().isBadRequest());   // no Idempotency-Key
        mvc.perform(post("/otp-requests").header("Idempotency-Key", "valid-key-03").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void anUnknownPathIs404() throws Exception {
        mvc.perform(post("/otp-request").header("Idempotency-Key", "valid-key-04")
                .contentType(MediaType.APPLICATION_JSON).content("{\"mobile\":\"9876543210\"}")).andExpect(status().isNotFound());
    }
}
