package com.dakroute.tracking;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import static org.assertj.core.api.Assertions.assertThat;

/** What support searches for: every log line of a request carries its id. */
@ExtendWith(OutputCaptureExtension.class)
class RequestIdLoggingTest extends ApiTest {

    @Test
    void theLookupsLogLineCarriesTheRequestId(CapturedOutput output) throws Exception {
        track("DKR100000002IN", "find-me-1234");
        assertThat(output.getOut()).containsPattern("INFO \\[rid:find-me-1234\\] .* Tracking lookup for DKR100000002IN: DELIVERED");
    }

    @Test
    void forgedLogTextInTheHeaderNeverReachesTheLog(CapturedOutput output) throws Exception {
        track("DKR100000001IN", "x\tERROR [rid:admin] payment refunded");
        assertThat(output.getOut()).doesNotContain("payment refunded");
    }
}
