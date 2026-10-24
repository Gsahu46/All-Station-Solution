package com.bimaly.policies;

import org.junit.jupiter.api.Test;

import static com.bimaly.policies.TestInsurer.INSURER;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PolicyContractTest extends ApiTest {

    @Test
    void aPolicyIsIssuedThroughTheInsurersSoapService() throws Exception {
        issue("term10", 1_000_000_000L).andExpect(status().isCreated())
                .andExpect(header().string("Location", org.hamcrest.Matchers.matchesRegex("/policies/SG-2026-\\d{6}")))
                .andExpect(jsonPath("$.productCode").value("TERM10")).andExpect(jsonPath("$.sumInsuredPaise").value(1_000_000_000L))
                .andExpect(jsonPath("$.premiumPaise").value(1_000_000L));
        var call = INSURER.calls.getFirst();
        assertThat(call.soapAction()).isEqualTo("\"http://insurer.example/policy/v1/IssuePolicy\"");
        assertThat(call.body()).contains("IssuePolicyRequest xmlns:ns2=\"http://insurer.example/policy/v1\"")
                .contains("<ns2:dateOfBirth>1988-04-12</ns2:dateOfBirth>").contains("<ns2:productCode>TERM10</ns2:productCode>");
    }

    @Test
    void theInsurersRefusalIs422WithItsReason() throws Exception {
        issue("TERM10", 60_000_000_000L).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.insurerCode").value("SUM_TOO_HIGH"))
                .andExpect(jsonPath("$.detail").value("The insurer refused the policy: The sum insured is above the limit for online issuance."));
    }

    @Test
    void theInsurersOwnFailureIs502AndASlowInsurer504() throws Exception {
        INSURER.broken = true;
        issue("TERM10", 1_000_000_000L).andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.detail").value("The insurer's system failed. Try again later."));
        INSURER.broken = false;
        INSURER.delayMillis = 2_000;
        issue("TERM10", 1_000_000_000L).andExpect(status().isGatewayTimeout())
                .andExpect(jsonPath("$.detail").value("The insurer did not answer in time. The policy may or may not have been issued: check before trying again."));
        assertThat(INSURER.calls).hasSize(2);   // never retried: a retry could issue a second policy
    }

    @Test
    void badRequestsAre400AndNeverReachTheInsurer() throws Exception {
        issue("{\"dateOfBirth\":\"1988-04-12\",\"productCode\":\"TERM10\",\"sumInsuredPaise\":1000}").andExpect(status().isBadRequest());
        issue("{\"customerName\":\"Meera\",\"dateOfBirth\":\"2999-01-01\",\"productCode\":\"TERM10\",\"sumInsuredPaise\":1000}").andExpect(status().isBadRequest());
        issue("{\"customerName\":\"Meera\",\"dateOfBirth\":\"1988-04-12\",\"productCode\":\"<x>&amp;\",\"sumInsuredPaise\":1000}").andExpect(status().isBadRequest());
        issue("TERM10", 0).andExpect(status().isBadRequest());
        assertThat(INSURER.calls).isEmpty();
    }
}
