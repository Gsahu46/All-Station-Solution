package com.basketo.referrals;

import org.junit.jupiter.api.Test;

import static com.basketo.referrals.TestWallet.WALLET;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: support fixes the cause of a DEAD credit, then sends it again with the same key. */
class RetryDeadCreditChallengeTest extends ApiTest {

    @Test
    void aDeadCreditIsSentAgainOnRequestAndPaidOnce() throws Exception {
        WALLET.planned.add(400);
        long customer = referredCustomer("9876500110", "device-new-0110");
        long reward = json(order(8201, customer, 60_000, "DELIVERED")).path("rewardId").asLong();
        awaitDelivery(reward, "DEAD");

        mvc.perform(post("/rewards/{id}/delivery-retry", reward).with(httpBasic("support", "support-demo-pass"))).andExpect(status().isAccepted());
        awaitDelivery(reward, "SENT");
        assertThat(WALLET.requests).hasSize(2).allMatch(r -> r.key().equals("referral-reward-" + reward));
        assertThat(WALLET.creditedTo(PRIYA)).isEqualTo(10_000);
    }

    @Test
    void onlyADeadCreditCanBeRetriedAndOnlyBySupport() throws Exception {
        long customer = referredCustomer("9876500111", "device-new-0111");
        long reward = json(order(8202, customer, 60_000, "DELIVERED")).path("rewardId").asLong();
        awaitDelivery(reward, "SENT");
        mvc.perform(post("/rewards/{id}/delivery-retry", reward).with(httpBasic("support", "support-demo-pass"))).andExpect(status().isConflict());
        mvc.perform(post("/rewards/{id}/delivery-retry", 999).with(httpBasic("support", "support-demo-pass"))).andExpect(status().isNotFound());
        mvc.perform(post("/rewards/{id}/delivery-retry", reward).with(httpBasic("orders", "orders-demo-pass"))).andExpect(status().isForbidden());
    }
}
