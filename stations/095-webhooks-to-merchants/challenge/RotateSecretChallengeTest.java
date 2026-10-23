package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /merchants/{id}/webhook-endpoints/{endpointId}/secret gives the endpoint a new secret. For 24
 * hours each request carries two signatures, so the merchant can switch over without missing a payment.
 */
class RotateSecretChallengeTest extends ApiTest {

    String rotate(String user, long merchantId, long endpointId) throws Exception {
        return json(mvc.perform(post("/merchants/{m}/webhook-endpoints/{e}/secret", merchantId, endpointId).with(httpBasic(user, password(user))))
                .andExpect(status().isCreated())).get("secret").asString();
    }

    @Test
    void bothSecretsWorkForADayThenOnlyTheNewOne() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            String old = secretFor("ravi", 1, merchant.url());
            String fresh = rotate("ravi", 1, 1);
            assertThat(fresh).startsWith("whsec_").isNotEqualTo(old);

            testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());
            CLOCK.advance(Duration.ofHours(23));
            dispatcher.dispatchDue();
            var duringSwitch = merchant.received().getLast();
            assertThat(duringSwitch.verifiedWith(old)).isTrue();
            assertThat(duringSwitch.verifiedWith(fresh)).isTrue();

            testEvent("ravi", 1, "PAY-1002", 49900).andExpect(status().isAccepted());
            CLOCK.advance(Duration.ofHours(2));   // 25 hours after the rotation
            dispatcher.dispatchDue();
            var afterADay = merchant.received().getLast();
            assertThat(afterADay.verifiedWith(old)).isFalse();
            assertThat(afterADay.verifiedWith(fresh)).isTrue();
        }
    }

    @Test
    void onlyYourOwnEndpointsSecretCanBeChanged() throws Exception {
        secretFor("meena", 2, "https://meena-dhaba.example/hooks");
        mvc.perform(post("/merchants/2/webhook-endpoints/1/secret").with(httpBasic("ravi", password("ravi")))).andExpect(status().isForbidden());
        mvc.perform(post("/merchants/1/webhook-endpoints/1/secret").with(httpBasic("ravi", password("ravi")))).andExpect(status().isNotFound());
        mvc.perform(post("/merchants/2/webhook-endpoints/1/secret")).andExpect(status().isUnauthorized());
    }
}
