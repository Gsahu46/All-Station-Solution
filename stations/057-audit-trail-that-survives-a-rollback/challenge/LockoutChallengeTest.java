package com.tijori.transfers;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: after 3 failed transfers from an account in the last 10 minutes, further transfers from it are 429
 * "Too many failed attempts" (and audited as failed attempts). The count comes from the audit trail, which only
 * works because failures survive their rollbacks. Other accounts are not affected. Demo rule, not a bank's.
 */
class LockoutChallengeTest extends ApiTest {

    @Test
    void threeFailuresLockTheSenderForAWhile() throws Exception {
        for (int i = 0; i < 3; i++) {
            transfer(2, 1, 500_000).andExpect(status().isUnprocessableContent());
        }
        transfer(2, 1, 1_000).andExpect(status().isTooManyRequests()).andExpect(jsonPath("$.title").value("Too many failed attempts"));
        assertThat(balance(2)).isEqualTo(10_000);
        transfer(1, 2, 1_000).andExpect(status().isCreated());   // Asha is not locked
        jdbc.sql("UPDATE audit_events SET at = at - interval '11 minutes'").update();
        transfer(2, 1, 1_000).andExpect(status().isCreated());   // ten minutes later, Ravi can try again
    }
}
