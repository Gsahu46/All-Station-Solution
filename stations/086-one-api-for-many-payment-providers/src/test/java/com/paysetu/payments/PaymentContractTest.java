package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PaymentContractTest extends ApiTest {

    @Test
    void aPaymentGoesToThePrimaryProvider() throws Exception {
        pay("ord-1001", 249900).andExpect(status().isCreated()).andExpect(jsonPath("$.id").value(1))
                .andExpect(jsonPath("$.orderId").value("ORD-1001")).andExpect(jsonPath("$.status").value("succeeded"))
                .andExpect(jsonPath("$.provider").value("sim-alpha")).andExpect(jsonPath("$.providerRef").value("ch_1"));
        assertThat(alpha.charges.get("pay_1").amount()).isEqualTo("2499.00");   // the adapter speaks sim-alpha's rupee text
    }

    @Test
    void aDeclineIsAnAnswerNotAFailover() throws Exception {
        pay("ORD-1002", 249951).andExpect(status().isPaymentRequired()).andExpect(jsonPath("$.status").value("declined"))
                .andExpect(jsonPath("$.declineReason").value("INSUFFICIENT_FUNDS"));
        assertThat(beta.authorisations).isEmpty();
    }

    @Test
    void anUnreachablePrimaryFailsOverAndBothDownIs503() throws Exception {
        alpha.fault = AlphaApi.Fault.CONNECTION_REFUSED;
        pay("ORD-1003", 100000).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-beta"));
        beta.down = true;
        pay("ORD-1004", 100000).andExpect(status().isServiceUnavailable()).andExpect(jsonPath("$.status").value("failed"));
    }

    @Test
    void badRequestsAre400AndUnknownPaymentsAre404() throws Exception {
        pay("OR", 100000).andExpect(status().isBadRequest());
        pay("ORD 1005", 100000).andExpect(status().isBadRequest());
        pay("ORD-1005", 99).andExpect(status().isBadRequest());
        pay("{\"orderId\":\"ORD-1005\",\"amountPaise\":2499.5}").andExpect(status().isBadRequest());
        pay("{\"orderId\":\"ORD-1005\"}").andExpect(status().isBadRequest());
        refund(42, 100).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such payment"));
        assertThat(column("SELECT count(*)::text FROM payments")).isEqualTo("0");
    }

    @Test
    void theSimulationsDemoAmountsTriggerItsFaults() throws Exception {
        pay("ORD-1006", 249997).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-alpha"));   // charged, then timed out
        pay("ORD-1007", 249998).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-beta"));    // refused, never charged
        assertThat(alpha.charges).containsOnlyKeys("pay_1");
    }
}
