package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RetryAndDeadLetterMessagingTest extends ApiTest {

    @Test
    void theWaitDoublesAfterEachFailureAndTheEighthFailureIsFinal() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            merchant.answer = () -> 500;   // never comes back
            secretFor("ravi", 1, merchant.url());
            testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());
            assertThat(dispatcher.dispatchDue()).isEqualTo(1);

            Instant at = T0;
            for (long wait : new long[]{30, 60, 120, 240, 480, 960, 1920}) {   // seconds: 30 s doubled each time
                at = at.plusSeconds(wait);
                CLOCK.set(at.minusSeconds(1));
                assertThat(dispatcher.dispatchDue()).as("one second early after waiting %d s", wait).isZero();
                CLOCK.set(at);
                assertThat(dispatcher.dispatchDue()).as("on time after waiting %d s", wait).isEqualTo(1);
            }
            assertThat(merchant.received()).hasSize(8);

            CLOCK.advance(Duration.ofDays(1));
            assertThat(dispatcher.dispatchDue()).isZero();   // dead-lettered: never sent again by itself
            deliveries("ravi", "?status=FAILED").andExpect(jsonPath("$.length()").value(1))
                    .andExpect(jsonPath("$[0].attempts").value(8)).andExpect(jsonPath("$[0].nextAttemptAt").doesNotExist())
                    .andExpect(jsonPath("$[0].lastError").value("HTTP 500"));
            assertThat(onlyDelivery("ravi").get("attempts")).hasSize(8);
        }
    }

    @Test
    void aSlowMerchantARedirectOrNoServerIsAFailedAttempt() throws Exception {
        try (TestMerchant slow = new TestMerchant(CLOCK); TestMerchant moved = new TestMerchant(CLOCK)) {
            slow.delayMillis = 1500;   // the timeout here is 500 ms
            moved.answer = () -> 302;
            TestMerchant gone = new TestMerchant(CLOCK);
            String goneUrl = gone.url();
            gone.close();   // nothing listens there any more
            secretFor("ravi", 1, slow.url());
            secretFor("ravi", 1, moved.url());
            secretFor("ravi", 1, goneUrl);
            testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());
            dispatcher.dispatchDue();

            deliveries("ravi", "?status=PENDING").andExpect(jsonPath("$.length()").value(3))
                    .andExpect(jsonPath("$[2].lastError").value("timed out after 500 ms"))
                    .andExpect(jsonPath("$[1].lastError").value("HTTP 302 (redirects are not followed)"))
                    .andExpect(jsonPath("$[0].lastError").value("could not connect"))
                    .andExpect(jsonPath("$[0].lastStatusCode").doesNotExist());
            assertThat(moved.received()).hasSize(1);   // /elsewhere was never asked
        }
    }
}
