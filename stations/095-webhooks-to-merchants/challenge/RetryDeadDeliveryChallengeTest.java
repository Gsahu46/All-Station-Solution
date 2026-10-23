package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: POST /webhook-deliveries/{id}/retry sends a dead-lettered delivery again, from the first attempt. */
class RetryDeadDeliveryChallengeTest extends ApiTest {

    @Test
    void aFailedDeliveryCanBeSentAgainOnceTheMerchantIsFixed() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            merchant.answer = () -> 500;
            secretFor("ravi", 1, merchant.url());
            testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());
            for (int i = 0; i < 8; i++) {   // eight failures, an hour apart: dead-lettered
                dispatcher.dispatchDue();
                CLOCK.advance(Duration.ofHours(1));
            }
            deliveries("ravi", "?status=FAILED").andExpect(jsonPath("$.length()").value(1));

            merchant.answer = () -> 200;   // the merchant fixed their server
            mvc.perform(post("/webhook-deliveries/1/retry").with(httpBasic("ravi", password("ravi")))).andExpect(status().isAccepted())
                    .andExpect(jsonPath("$.status").value("PENDING")).andExpect(jsonPath("$.attempts").value(0))
                    .andExpect(jsonPath("$.nextAttemptAt").value("2026-10-23T18:00:00Z"));
            assertThat(dispatcher.dispatchDue()).isEqualTo(1);

            deliveries("ravi", "?status=DELIVERED").andExpect(jsonPath("$.length()").value(1));
            assertThat(onlyDelivery("ravi").get("attempts")).hasSize(9);   // the history is kept
        }
    }

    @Test
    void onlyYourOwnFailedDeliveriesCanBeRetried() throws Exception {
        secretFor("ravi", 1, "https://ravi-kirana.example/hooks/paysetu");
        testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());
        mvc.perform(post("/webhook-deliveries/1/retry").with(httpBasic("ravi", password("ravi")))).andExpect(status().isConflict());   // still pending
        mvc.perform(post("/webhook-deliveries/1/retry").with(httpBasic("meena", password("meena")))).andExpect(status().isNotFound());
        mvc.perform(post("/webhook-deliveries/99/retry").with(httpBasic("ravi", password("ravi")))).andExpect(status().isNotFound());
        mvc.perform(post("/webhook-deliveries/1/retry")).andExpect(status().isUnauthorized());
    }
}
