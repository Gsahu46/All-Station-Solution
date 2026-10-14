package com.dakroute.tracking;

import io.micrometer.core.instrument.MeterRegistry;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The failure drill, as a test: the tracking store goes down, and everything the runbook relies on must be there.
 * The answer says to come back, the error is logged once at ERROR with the request id, and the metric moves.
 */
@ExtendWith(OutputCaptureExtension.class)
class OperationsDrillTest extends ApiTest {

    @Autowired
    Shipments shipments;
    @Autowired
    MeterRegistry metrics;

    double count(String outcome) {
        var c = metrics.find("tracking.lookups").tag("outcome", outcome).counter();
        return c == null ? 0 : c.count();
    }

    @AfterEach
    void endTheOutage() {
        shipments.simulateOutage(false);
    }

    @Test
    void duringAnOutageEveryTraceTheRunbookNeedsIsThere(CapturedOutput output) throws Exception {
        double errorsBefore = count("error");
        shipments.simulateOutage(true);

        track("DKR100000001IN", "drill-req-0001")
                .andExpect(status().isServiceUnavailable())
                .andExpect(header().string("Retry-After", "60"))
                .andExpect(header().string("X-Request-Id", "drill-req-0001"))
                .andExpect(jsonPath("$.requestId").value("drill-req-0001"));

        assertThat(output.getOut()).containsPattern("ERROR \\[rid:drill-req-0001\\] .* Tracking lookup for DKR100000001IN failed");
        assertThat(count("error")).isEqualTo(errorsBefore + 1);
    }

    @Test
    void afterTheOutageLookupsRecover() throws Exception {
        shipments.simulateOutage(true);
        track("DKR100000002IN").andExpect(status().isServiceUnavailable());
        shipments.simulateOutage(false);
        track("DKR100000002IN").andExpect(status().isOk());
    }

    @Test
    void theMetricIsPublishedWhereTheAlertReadsIt() throws Exception {
        track("DKR100000002IN");
        mvc.perform(get("/actuator/metrics/tracking.lookups").param("tag", "outcome:found"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("tracking.lookups"))
                .andExpect(jsonPath("$.measurements[0].value").isNumber());
    }
}
