package com.basketo.referrals;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: at most N rewards a calendar month (India time) per referrer; 2 here. */
@TestPropertySource(properties = "basketo.referrals.max-rewards-per-month=2")
class MonthlyLimitChallengeTest extends ApiTest {

    @Test
    void theThirdRewardThisMonthWaitsAndTheReferralStaysOpen() throws Exception {
        long a = referredCustomer("9876500101", "device-new-0101");
        long b = referredCustomer("9876500102", "device-new-0102");
        long c = referredCustomer("9876500103", "device-new-0103");
        order(8101, a, 60_000, "DELIVERED").andExpect(status().isCreated());
        order(8102, b, 60_000, "DELIVERED").andExpect(status().isCreated());
        order(8103, c, 60_000, "DELIVERED").andExpect(status().isOk()).andExpect(jsonPath("$.outcome").value("MONTHLY_LIMIT"));
        assertThat(count("rewards")).isEqualTo(2);
        assertThat(jdbc.sql("SELECT status FROM referrals WHERE referee_id = ?").param(c).query(String.class).single()).isEqualTo("PENDING");
    }

    @Test
    void anotherReferrersRewardsDoNotCount() throws Exception {
        long a = referredCustomer("9876500104", "device-new-0104");
        long b = referredCustomer("9876500105", "device-new-0105");
        long k = json(signUp("KARAN50", "9876500106", "device-new-0106")).path("customerId").asLong();
        order(8104, a, 60_000, "DELIVERED").andExpect(status().isCreated());
        order(8105, b, 60_000, "DELIVERED").andExpect(status().isCreated());
        order(8106, k, 60_000, "DELIVERED").andExpect(status().isCreated());
    }
}
