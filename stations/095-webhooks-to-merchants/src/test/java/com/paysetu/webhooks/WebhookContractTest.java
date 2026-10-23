package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class WebhookContractTest extends ApiTest {

    @Test
    void anEndpointIsRegisteredWithASecretShownOnce() throws Exception {
        registerEndpoint("ravi", 1, "https://ravi-kirana.example/hooks/paysetu").andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(1))
                .andExpect(jsonPath("$.url").value("https://ravi-kirana.example/hooks/paysetu"))
                .andExpect(jsonPath("$.secret").value(org.hamcrest.Matchers.matchesRegex("whsec_[A-Za-z0-9+/]{32}")))
                .andExpect(jsonPath("$.createdAt").value("2026-10-23T10:00:00Z"));
        registerEndpoint("ravi", 1, "https://ravi-kirana.example/hooks/paysetu").andExpect(status().isConflict());
        registerEndpoint("ravi", 1, "not a url").andExpect(status().isBadRequest());
        registerEndpoint("ravi", 1, "ftp://ravi-kirana.example/hooks").andExpect(status().isBadRequest());
        registerEndpoint("ravi", 1, "").andExpect(status().isBadRequest());
        // Another merchant may use the same URL (a shared platform); it gets its own secret.
        registerEndpoint("meena", 2, "https://ravi-kirana.example/hooks/paysetu").andExpect(status().isCreated());
    }

    @Test
    void aPaymentIsSentSignedTheStandardWebhooksWay() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            String secret = secretFor("ravi", 1, merchant.url());
            var recorded = json(testEvent("ravi", 1, "pay-1001", 49900).andExpect(status().isAccepted()));
            assertThat(recorded.get("paymentRef").asString()).isEqualTo("PAY-1001");
            assertThat(recorded.get("deliveries").asInt()).isEqualTo(1);
            assertThat(merchant.received()).isEmpty();   // nothing is sent inside the request

            assertThat(dispatcher.dispatchDue()).isEqualTo(1);

            var got = merchant.received().getFirst();
            assertThat(got.id()).isEqualTo(recorded.get("eventId").asString());
            assertThat(got.timestamp()).isEqualTo(String.valueOf(T0.getEpochSecond()));
            assertThat(got.contentType()).isEqualTo("application/json");
            assertThat(got.body()).isEqualTo("{\"type\":\"payment.captured\",\"timestamp\":\"2026-10-23T10:00:00Z\",\"data\":{\"paymentRef\":\"PAY-1001\",\"amountPaise\":49900}}");
            assertThat(got.signature()).isEqualTo(WebhookSignature.sign(secret, got.id(), T0.getEpochSecond(), got.body()));
            assertThat(got.verifiedWith(secret)).isTrue();
            assertThat(dispatcher.dispatchDue()).isZero();   // delivered: not sent again
        }
    }

    @Test
    void theDeliveryLogListsByStatusAndShowsEveryAttempt() throws Exception {
        try (TestMerchant up = new TestMerchant(CLOCK); TestMerchant down = new TestMerchant(CLOCK)) {
            down.answer = () -> 503;
            secretFor("ravi", 1, up.url());
            secretFor("ravi", 1, down.url());
            testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted()).andExpect(jsonPath("$.deliveries").value(2));
            dispatcher.dispatchDue();

            deliveries("ravi", "").andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(2))
                    .andExpect(jsonPath("$[0].id").value(2)).andExpect(jsonPath("$[1].id").value(1))
                    .andExpect(jsonPath("$[0].secret").doesNotExist());
            deliveries("ravi", "?status=DELIVERED").andExpect(jsonPath("$.length()").value(1))
                    .andExpect(jsonPath("$[0].endpointUrl").value(up.url())).andExpect(jsonPath("$[0].deliveredAt").value("2026-10-23T10:00:00Z"));
            deliveries("ravi", "?status=PENDING").andExpect(jsonPath("$.length()").value(1))
                    .andExpect(jsonPath("$[0].endpointUrl").value(down.url()))
                    .andExpect(jsonPath("$[0].paymentRef").value("PAY-1001")).andExpect(jsonPath("$[0].type").value("payment.captured"))
                    .andExpect(jsonPath("$[0].attempts").value(1)).andExpect(jsonPath("$[0].lastStatusCode").value(503))
                    .andExpect(jsonPath("$[0].lastError").value("HTTP 503")).andExpect(jsonPath("$[0].nextAttemptAt").value("2026-10-23T10:00:30Z"));
            deliveries("ravi", "?status=FAILED").andExpect(jsonPath("$.length()").value(0));
            deliveries("ravi", "?status=LOST").andExpect(status().isBadRequest());

            mvc.perform(get("/webhook-deliveries/2").with(httpBasic("ravi", password("ravi")))).andExpect(status().isOk())
                    .andExpect(jsonPath("$.delivery.status").value("PENDING"))
                    .andExpect(jsonPath("$.attempts.length()").value(1))
                    .andExpect(jsonPath("$.attempts[0].attemptedAt").value("2026-10-23T10:00:00Z"))
                    .andExpect(jsonPath("$.attempts[0].statusCode").value(503));
            mvc.perform(get("/webhook-deliveries/999").with(httpBasic("ravi", password("ravi")))).andExpect(status().isNotFound());
        }
    }
}
