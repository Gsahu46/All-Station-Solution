package com.kartwala.refunds;

import io.micrometer.core.instrument.MeterRegistry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The failure drill, as a test: the ledger fails, and everything the triage runbook relies on must be there. The
 * caller sees a 500 with the request id, the log has one ERROR line with that id and the stack trace, the metric moves.
 */
@ExtendWith(OutputCaptureExtension.class)
class OperationsDrillTest extends ApiTest {

    @Autowired
    RefundLedger ledger;
    @Autowired
    MeterRegistry metrics;

    double failed() {
        var c = metrics.find("refunds.requests").tag("outcome", "failed").counter();
        return c == null ? 0 : c.count();
    }

    @Test
    void anUnexpectedErrorLeavesATrailFromTheCustomerToTheStackTrace(CapturedOutput output) throws Exception {
        ledger.simulateFailure(true);
        refund("""
                {"orderId":"KW-1042","lineIds":["L2"]}""", "drill-req-0001")
                .andExpect(status().isInternalServerError())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(header().string("X-Request-Id", "drill-req-0001"))
                .andExpect(jsonPath("$.requestId").value("drill-req-0001"))
                .andExpect(jsonPath("$.detail").value("The refund was not recorded. Please try again; if it fails again, quote request id drill-req-0001 to support."));
        assertThat(output.getOut())
                .containsPattern("ERROR \\[rid:drill-req-0001\\] .* Refund request failed")
                .contains("java.lang.IllegalStateException: Refund ledger did not answer (failure drill)")
                .containsPattern("at com\\.kartwala\\.refunds\\.RefundLedger\\.failIfDrill");
        assertThat(failed()).isEqualTo(1);
    }

    @Test
    void afterTheFailureRefundsRecover() throws Exception {
        ledger.simulateFailure(true);
        refund("""
                {"orderId":"KW-1042","lineIds":["L2"]}""").andExpect(status().isInternalServerError());
        ledger.simulateFailure(false);
        refund("""
                {"orderId":"KW-1042","lineIds":["L2"]}""").andExpect(status().isCreated());   // nothing was recorded by the failed try
    }

    @Test
    void clientMistakesAreNotCountedAsFailuresAndTheMetricIsPublished() throws Exception {
        refund("""
                {"orderId":"KW-9999"}""").andExpect(status().isNotFound());
        refund("""
                {"orderId":"KW-1042","lineIds":["L2"]}""").andExpect(status().isCreated());
        assertThat(failed()).isZero();
        mvc.perform(get("/actuator/metrics/refunds.requests").param("tag", "outcome:recorded"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.measurements[0].value").value(1.0));
    }
}
