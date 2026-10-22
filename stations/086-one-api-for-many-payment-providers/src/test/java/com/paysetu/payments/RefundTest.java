package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RefundTest extends ApiTest {

    @Test
    void partRefundsUpToTheAmountAndNoMore() throws Exception {
        pay("ORD-3001", 100000);
        refund(1, 40000).andExpect(status().isCreated()).andExpect(jsonPath("$.status").value("succeeded")).andExpect(jsonPath("$.provider").value("sim-alpha"));
        refund(1, 60000).andExpect(status().isCreated());
        refund(1, 1).andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("At most 0 paise can still be refunded"));
        assertThat(alpha.refunds).containsExactly("ch_1 400.00", "ch_1 600.00");
    }

    @Test
    void aRefundGoesToTheProviderThatTookThePayment() throws Exception {
        alpha.fault = AlphaApi.Fault.CONNECTION_REFUSED;
        pay("ORD-3002", 100000).andExpect(jsonPath("$.provider").value("sim-beta"));
        alpha.fault = AlphaApi.Fault.NONE;   // alpha is back and still primary
        refund(1, 25000).andExpect(status().isCreated()).andExpect(jsonPath("$.provider").value("sim-beta"));
        assertThat(beta.reversals).containsExactly("T5001 25000");
        assertThat(alpha.refunds).isEmpty();
    }

    @Test
    void onlySucceededPaymentsCanBeRefunded() throws Exception {
        pay("ORD-3003", 100051);
        refund(1, 100).andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("Only a succeeded payment can be refunded; this one is declined"));
    }

    @Test
    void aRefundTheProviderNeverGotGivesTheAmountBack() throws Exception {
        pay("ORD-3004", 100000);
        alpha.fault = AlphaApi.Fault.CONNECTION_REFUSED;
        refund(1, 100000).andExpect(status().isServiceUnavailable());
        assertThat(column("SELECT refunded_paise::text FROM payments")).isEqualTo("0");
        assertThat(column("SELECT status FROM refunds")).isEqualTo("failed");
        alpha.fault = AlphaApi.Fault.NONE;
        refund(1, 100000).andExpect(status().isCreated());
    }
}
