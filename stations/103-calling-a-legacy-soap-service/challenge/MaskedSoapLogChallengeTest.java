package com.bimaly.policies;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: when the insurer disputes a policy, support needs the exact envelopes. Log each request and response
 * envelope at DEBUG (logger com.bimaly.policies.SoapLog), with the customer's name replaced by ***.
 */
@ExtendWith(OutputCaptureExtension.class)
@TestPropertySource(properties = "logging.level.com.bimaly.policies.SoapLog=DEBUG")
class MaskedSoapLogChallengeTest extends ApiTest {

    @Test
    void envelopesAreLoggedWithoutTheCustomersName(CapturedOutput output) throws Exception {
        issue("TERM10", 1_000_000_000L).andExpect(status().isCreated());
        assertThat(output.getOut()).contains("IssuePolicyRequest").contains("customerName>***</").contains("IssuePolicyResponse")
                .doesNotContain("Meera Iyer");
    }

    @Test
    void faultsAreLoggedToo(CapturedOutput output) throws Exception {
        issue("CAR1", 1_000_000_000L).andExpect(status().isUnprocessableContent());
        assertThat(output.getOut()).contains("PRODUCT_UNKNOWN").doesNotContain("Meera Iyer");
    }
}
