package com.tijori.wallets;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /wallets/{id}/top-ups/{topUpId}/reversal, for a top-up whose money never arrived. The balance goes
 * back down, the amount no longer counts towards today's limit, and a second reversal answers the same. A V3 migration
 * adds reversed_at, and the database rule stops counting reversed top-ups.
 */
class ReversalChallengeTest extends ApiTest {

    ResultActions reverse(long wallet, long topUpId) throws Exception {
        return mvc.perform(post("/wallets/{id}/top-ups/{topUpId}/reversal", wallet, topUpId));
    }

    @Test
    void aReversedTopUpFreesTheLimitAndIsReversedOnce() throws Exception {
        topUp(ANANYA, 1000000).andExpect(status().isCreated());
        reverse(ANANYA, 1).andExpect(status().isOk()).andExpect(jsonPath("$.balancePaise").value(50000));
        reverse(ANANYA, 1).andExpect(status().isOk()).andExpect(jsonPath("$.balancePaise").value(50000));
        topUp(ANANYA, 1000000).andExpect(status().isCreated()).andExpect(jsonPath("$.toppedUpTodayPaise").value(1000000));
        assertThat(balance(ANANYA)).isEqualTo(1050000);
    }

    @Test
    void aSpentTopUpCannotBeReversedAndUnknownOnesAre404() throws Exception {
        topUp(ANANYA, 300000).andExpect(status().isCreated());
        jdbc.sql("UPDATE wallets SET balance_paise = 100000 WHERE id = 1001").update();   // most of it was spent
        reverse(ANANYA, 1).andExpect(status().isConflict());
        reverse(ANANYA, 99).andExpect(status().isNotFound());
        reverse(VIKRAM, 1).andExpect(status().isNotFound());   // not this wallet's top-up
        assertThat(balance(ANANYA)).isEqualTo(100000);
    }

    @Test
    void theDatabaseRuleSkipsReversedTopUps() {
        jdbc.sql("INSERT INTO top_ups (wallet_id, amount_paise, reversed_at) VALUES (1001, 1000000, now())").update();
        jdbc.sql("INSERT INTO top_ups (wallet_id, amount_paise) VALUES (1001, 1000000)").update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO top_ups (wallet_id, amount_paise) VALUES (1001, 100)").update())
                .hasMessageContaining("top_ups_within_daily_limit");
    }
}
