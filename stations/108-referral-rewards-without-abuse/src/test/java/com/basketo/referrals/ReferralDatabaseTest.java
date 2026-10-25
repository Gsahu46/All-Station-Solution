package com.basketo.referrals;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The rules hold for any writer: plain SQL, no Java in between. */
class ReferralDatabaseTest extends ApiTest {

    @Test
    void theRulesAreNamedConstraintsInTheDatabase() throws Exception {
        long c = referredCustomer("9876500040", "device-new-0040");
        long referral = jdbc.sql("SELECT id FROM referrals WHERE referee_id = ?").param(c).query(Long.class).single();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO referrals (referrer_id, referee_id, device_id, status) VALUES (2, 2, 'device-x-1', 'PENDING')").update())
                .hasMessageContaining("referrals_not_self");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO referrals (referrer_id, referee_id, device_id, status) VALUES (2, ?, 'device-x-2', 'PENDING')").param(c).update())
                .hasMessageContaining("referrals_one_per_referee");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO referrals (referrer_id, referee_id, device_id, status) VALUES (1, 2, 'device-new-0040', 'PENDING')").update())
                .hasMessageContaining("referrals_one_per_device");
        assertThatThrownBy(() -> jdbc.sql("UPDATE referrals SET status = 'PAID' WHERE id = ?").param(referral).update())
                .hasMessageContaining("referrals_status");
        jdbc.sql("INSERT INTO rewards (referral_id, order_id, referrer_id, amount_paise) VALUES (?, 7301, 1, 10000)").param(referral).update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO rewards (referral_id, order_id, referrer_id, amount_paise) VALUES (?, 7302, 1, 10000)").param(referral).update())
                .hasMessageContaining("rewards_one_per_referral");
        assertThatThrownBy(() -> jdbc.sql("UPDATE rewards SET amount_paise = 0").update())
                .hasMessageContaining("rewards_amount_positive");
        assertThatThrownBy(() -> jdbc.sql("UPDATE customers SET phone = '+919812345670' WHERE id = 2").update())
                .hasMessageContaining("customers_phone_unique");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO wallet_outbox (reward_id, status) SELECT id, 'LOST' FROM rewards").update())
                .hasMessageContaining("wallet_outbox_status");
    }

    @Test
    void aSignUpThatCannotRecordItsReferralLeavesNoCustomerBehind() throws Exception {
        // Another referral already holds this device (written by some other path); the customer check alone misses it.
        long other = referredCustomer("9876500041", "device-new-0041");
        jdbc.sql("UPDATE referrals SET device_id = 'device-taken-99' WHERE referee_id = ?").param(other).update();
        signUp("KARAN50", "9876500042", "device-taken-99").andExpect(status().isUnprocessableContent());
        assertThat(jdbc.sql("SELECT count(*) FROM customers WHERE phone = '+919876500042'").query(Integer.class).single()).isZero();
    }
}
