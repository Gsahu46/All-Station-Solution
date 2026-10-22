package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old code treated any error from the first provider as "it failed" and charged the second one.
 * sim-alpha charges, then its answer times out: the customer was charged by both providers.
 */
class FailoverAfterTimeoutTrapTest extends ApiTest {

    @Test
    void theOldCodeChargedTheCustomerTwice() {
        alpha.fault = AlphaApi.Fault.TIMEOUT_AFTER_CHARGING;
        try {
            alpha.createCharge("pay_1", "2499.00");
        } catch (AlphaApi.ReadTimeout timeout) {
            beta.authorise("pay_1", 249900);   // "alpha failed, try beta"
        }
        assertThat(alpha.charges).containsKey("pay_1");
        assertThat(beta.authorisations).containsKey("pay_1");   // charged twice for one order
    }

    @Test
    void afterATimeoutTheApiAsksFirstAndFindsTheCharge() throws Exception {
        alpha.fault = AlphaApi.Fault.TIMEOUT_AFTER_CHARGING;
        pay("ORD-1001", 249900).andExpect(status().isCreated()).andExpect(jsonPath("$.status").value("succeeded"))
                .andExpect(jsonPath("$.provider").value("sim-alpha")).andExpect(jsonPath("$.providerRef").value("ch_1"));
        assertThat(beta.authorisations).isEmpty();
    }

    @Test
    void whenTheStatusCheckCannotSayEitherNoOtherProviderIsTried() throws Exception {
        alpha.fault = AlphaApi.Fault.TIMEOUT_AFTER_CHARGING;
        alpha.lookupDown = true;
        pay("ORD-1001", 249900).andExpect(status().isAccepted()).andExpect(jsonPath("$.status").value("unknown"))
                .andExpect(jsonPath("$.provider").value("sim-alpha"));
        assertThat(beta.authorisations).isEmpty();
    }

    @Test
    void whenTheProviderSaysItNeverChargedTheFallbackIsTried() throws Exception {
        alpha.fault = AlphaApi.Fault.TIMEOUT_BEFORE_CHARGING;
        pay("ORD-1001", 249900).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-beta"))
                .andExpect(jsonPath("$.providerRef").value("T5001"));
        assertThat(alpha.charges).isEmpty();
    }
}
