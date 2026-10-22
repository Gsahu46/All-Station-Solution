package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Switching provider is configuration: no code changes, and the stored payment says which one took it. */
@TestPropertySource(properties = {"paysetu.primary=sim-beta", "paysetu.fallback="})
class PrimaryFromConfigTest extends ApiTest {

    @Test
    void sim_betaAsPrimaryWithNoFallback() throws Exception {
        pay("ORD-4001", 77700).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-beta")).andExpect(jsonPath("$.providerRef").value("T5001"));
        beta.down = true;
        pay("ORD-4002", 77700).andExpect(status().isServiceUnavailable());
        assertThat(alpha.charges).isEmpty();
    }
}
