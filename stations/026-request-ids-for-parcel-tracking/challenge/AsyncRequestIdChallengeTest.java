package com.dakroute.tracking;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /shipments/{awb}/eta works out the delivery estimate on a worker thread. The MDC belongs to one
 * thread, so the worker's log line loses the request id unless the executor copies it across (a TaskDecorator).
 */
@ExtendWith(OutputCaptureExtension.class)
class AsyncRequestIdChallengeTest extends ApiTest {

    @Test
    void theWorkerThreadLogsUnderTheSameRequestId(CapturedOutput output) throws Exception {
        mvc.perform(get("/shipments/DKR100000001IN/eta").header("X-Request-Id", "eta-request-0001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.estimate").value("TODAY"));
        assertThat(output.getOut()).containsPattern("\\[rid:eta-request-0001\\] .*eta-worker.* Estimated DKR100000001IN: TODAY");
    }
}
