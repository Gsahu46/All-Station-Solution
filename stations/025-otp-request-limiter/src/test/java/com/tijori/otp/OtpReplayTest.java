package com.tijori.otp;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The same request twice is one request: one slot, one SMS, one answer. */
class OtpReplayTest extends ApiTest {

    String requestId(String key, String mobile) throws Exception {
        return JsonPath.read(otp(key, mobile).andExpect(status().isAccepted()).andReturn().getResponse().getContentAsString(), "$.requestId");
    }

    @Test
    void aRetryWithTheSameKeyGetsTheSameAnswerAndNoSecondSms() throws Exception {
        String first = requestId("tap-0001-retry", "9876543210");
        String again = requestId("tap-0001-retry", "+91 98765 43210");   // the same number, written differently
        assertThat(again).isEqualTo(first);
        assertThat(sms.sentTo("9876543210")).isEqualTo(1);
        otp("tap-0002-next", "9876543210").andExpect(jsonPath("$.attemptsLeft").value(1));   // the retry used no slot
    }

    @Test
    void tenCopiesOfOneRequestAtTheSameInstantAreOneRequest() throws Exception {
        Set<String> ids = ConcurrentHashMap.newKeySet();
        CountDownLatch start = new CountDownLatch(1);
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 10; i++) {
                threads.submit(() -> {
                    start.await();
                    ids.add(requestId("double-tap-777", "9876543210"));
                    return null;
                });
            }
            start.countDown();
        }
        assertThat(ids).hasSize(1);
        assertThat(sms.sentTo("9876543210")).isEqualTo(1);
    }

    @Test
    void aKeyReusedForAnotherNumberIs422() throws Exception {
        requestId("shared-key-01", "9876543210");
        otp("shared-key-01", "9123456780").andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.title").value("Idempotency key reused"));
        assertThat(sms.sentTo("9123456780")).isZero();
    }

    @Test
    void aRefusedRequestCanBeRetriedWithItsKeyOnceTheWindowMoves() throws Exception {
        for (int i = 0; i < 3; i++) {
            requestId("fill-" + i + "-abcdef", "9876543210");
        }
        otp("late-key-0001", "9876543210").andExpect(status().isTooManyRequests());
        clock.advance(Duration.ofMinutes(10));
        otp("late-key-0001", "9876543210").andExpect(status().isAccepted());   // the refusal had no effect to replay
    }
}
