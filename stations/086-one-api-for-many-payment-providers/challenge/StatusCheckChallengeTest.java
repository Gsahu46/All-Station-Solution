package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /payments/{id}/status-check settles an "unknown" payment by asking the provider that took it:
 * charged, declined, or never seen (then "failed": nothing was charged). If it still cannot say, the payment stays unknown.
 */
class StatusCheckChallengeTest extends ApiTest {

    ResultActions check(long id) throws Exception {
        return mvc.perform(post("/payments/{id}/status-check", id));
    }

    void unknownPayment(AlphaApi.Fault fault) throws Exception {
        alpha.fault = fault;
        alpha.lookupDown = true;
        pay("ORD-7001", 50000).andExpect(jsonPath("$.status").value("unknown"));
        alpha.fault = AlphaApi.Fault.NONE;
    }

    @Test
    void aChargeThatHappenedBecomesSucceeded() throws Exception {
        unknownPayment(AlphaApi.Fault.TIMEOUT_AFTER_CHARGING);
        check(1).andExpect(status().isAccepted());   // still cannot say
        alpha.lookupDown = false;
        check(1).andExpect(status().isCreated()).andExpect(jsonPath("$.status").value("succeeded")).andExpect(jsonPath("$.providerRef").value("ch_1"));
        assertThat(beta.authorisations).isEmpty();
    }

    @Test
    void aChargeThatNeverHappenedBecomesFailed() throws Exception {
        unknownPayment(AlphaApi.Fault.TIMEOUT_BEFORE_CHARGING);
        alpha.lookupDown = false;
        check(1).andExpect(status().isServiceUnavailable()).andExpect(jsonPath("$.status").value("failed"));
        assertThat(alpha.charges).isEmpty();
    }

    @Test
    void settledPaymentsAreLeftAsTheyAre() throws Exception {
        pay("ORD-7002", 50000).andExpect(status().isCreated());
        alpha.lookupDown = true;   // a settled payment needs no question
        check(1).andExpect(status().isCreated()).andExpect(jsonPath("$.status").value("succeeded"));
        check(42).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such payment"));
    }
}
