package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: add the simulated provider sim-gamma (GammaApi, in the solution) with an adapter, and make it primary by
 * configuration alone. The payments code does not change; a V3 migration lets the database store the new name.
 */
@TestPropertySource(properties = {"paysetu.primary=sim-gamma", "paysetu.fallback=sim-alpha"})
class ThirdProviderChallengeTest extends ApiTest {

    @Autowired
    GammaApi gamma;

    @Test
    void sim_gammaTakesPaymentsAndItsErrorsMapToOurs() throws Exception {
        gamma.reset();
        pay("ORD-8001", 120000).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-gamma"))
                .andExpect(jsonPath("$.providerRef").value("g-1"));
        pay("ORD-8002", 120051).andExpect(status().isPaymentRequired()).andExpect(jsonPath("$.declineReason").value("INSUFFICIENT_FUNDS"));
        refund(1, 20000).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-gamma"));
        assertThat(gamma.refunds).containsExactly("g-1 20000");
        assertThat(alpha.charges).isEmpty();
    }

    @Test
    void whenSim_gammaIsUnreachableSimAlphaTakesOver() throws Exception {
        gamma.reset();
        gamma.unreachable = true;
        pay("ORD-8003", 120000).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-alpha"));
    }
}
