package com.tijori.wallets;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class TopUpContractTest extends ApiTest {

    @Test
    void aTopUpWithinTheLimitIsRecorded() throws Exception {
        topUp(ANANYA, 400000).andExpect(status().isCreated()).andExpect(jsonPath("$.amountPaise").value(400000))
                .andExpect(jsonPath("$.balancePaise").value(450000)).andExpect(jsonPath("$.toppedUpTodayPaise").value(400000))
                .andExpect(jsonPath("$.dailyLimitPaise").value(1000000)).andExpect(jsonPath("$.createdAt").value("2026-10-30T06:30:00Z"));
    }

    @Test
    void exactlyTheLimitIsAllowedAndOnePaisaMoreIsNot() throws Exception {
        topUp(ANANYA, 600000).andExpect(status().isCreated());
        topUp(ANANYA, 400001).andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("The daily limit for minimum-KYC wallets is ₹10,000.00; ₹6,000.00 was topped up today (IST), so at most ₹4,000.00 more"))
                .andExpect(jsonPath("$.remainingTodayPaise").value(400000));
        topUp(ANANYA, 400000).andExpect(status().isCreated()).andExpect(jsonPath("$.toppedUpTodayPaise").value(1000000));
        assertThat(balance(ANANYA)).isEqualTo(50000 + 1000000);
    }

    @Test
    void theLimitDependsOnTheKycTier() throws Exception {
        topUp(VIKRAM, 5000000).andExpect(status().isCreated());
        topUp(VIKRAM, 5000000).andExpect(status().isCreated()).andExpect(jsonPath("$.dailyLimitPaise").value(10000000));
        topUp(VIKRAM, 100).andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("The daily limit for full-KYC wallets is ₹1,00,000.00; ₹1,00,000.00 was topped up today (IST), so at most ₹0.00 more"));
    }

    @Test
    void unknownWalletsAre404AndBadAmountsAre400() throws Exception {
        topUp(9999, 100000).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such wallet"));
        topUp(ANANYA, 99).andExpect(status().isBadRequest());
        topUp(ANANYA, 10_000_001).andExpect(status().isBadRequest());
        topUp(ANANYA, "{\"amountPaise\": 4000.5}").andExpect(status().isBadRequest());
        topUp(ANANYA, "{}").andExpect(status().isBadRequest());
        assertThat(toppedUp(ANANYA)).isZero();
    }

    @Test
    void amountsAreShownWithIndianDigitGrouping() {
        assertThat(TopUps.rupees(0)).isEqualTo("₹0.00");
        assertThat(TopUps.rupees(99999)).isEqualTo("₹999.99");
        assertThat(TopUps.rupees(1000000)).isEqualTo("₹10,000.00");
        assertThat(TopUps.rupees(10000005)).isEqualTo("₹1,00,000.05");
        assertThat(TopUps.rupees(123456789012L)).isEqualTo("₹1,23,45,67,890.12");
    }
}
