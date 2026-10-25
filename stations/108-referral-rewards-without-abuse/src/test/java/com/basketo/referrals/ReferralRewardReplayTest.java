package com.basketo.referrals;

import org.junit.jupiter.api.Test;

import java.util.List;

import static com.basketo.referrals.ReferralAbuseTrapTest.atOnce;
import static com.basketo.referrals.TestWallet.WALLET;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The order service delivers each event at least once: the same "delivered" may arrive twice, or twenty times at once. */
class ReferralRewardReplayTest extends ApiTest {

    @Test
    void theSameEventTwiceGivesOneReward() throws Exception {
        long customer = referredCustomer("9876500020", "device-new-0020");
        long reward = json(order(7101, customer, 70_000, "DELIVERED").andExpect(status().isCreated())).path("rewardId").asLong();
        order(7101, customer, 70_000, "DELIVERED").andExpect(status().isOk())
                .andExpect(jsonPath("$.outcome").value("ALREADY_REWARDED")).andExpect(jsonPath("$.rewardId").value(reward));
        awaitDelivery(reward, "SENT");
        assertThat(count("rewards")).isEqualTo(1);
        assertThat(count("wallet_outbox")).isEqualTo(1);
        assertThat(WALLET.creditedTo(PRIYA)).isEqualTo(10_000);
    }

    @Test
    void aSecondDeliveredOrderOfTheSameCustomerIsNotASecondReward() throws Exception {
        long customer = referredCustomer("9876500021", "device-new-0021");
        long reward = json(order(7102, customer, 70_000, "DELIVERED")).path("rewardId").asLong();
        order(7103, customer, 90_000, "DELIVERED").andExpect(status().isOk())
                .andExpect(jsonPath("$.outcome").value("ALREADY_REWARDED")).andExpect(jsonPath("$.rewardId").value(reward));
        assertThat(count("rewards")).isEqualTo(1);
    }

    @Test
    void twentyCopiesAtTheSameMomentGiveOneReward() throws Exception {
        long customer = referredCustomer("9876500022", "device-new-0022");
        List<Integer> statuses = atOnce(20, i -> order(7104, customer, 70_000, "DELIVERED").andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(1);
        assertThat(statuses).filteredOn(s -> s == 200).hasSize(19);
        assertThat(count("rewards")).isEqualTo(1);
        assertThat(count("wallet_outbox")).isEqualTo(1);
    }
}
