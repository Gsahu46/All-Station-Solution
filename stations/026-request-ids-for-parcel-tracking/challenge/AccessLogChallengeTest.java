package com.dakroute.tracking;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Challenge 1: one INFO line when each request ends: method, path, status and how long it took, under the request's
 * id. Support can then see every request a customer made, not only the ones that logged something.
 */
@ExtendWith(OutputCaptureExtension.class)
class AccessLogChallengeTest extends ApiTest {

    @Test
    void everyRequestEndsWithOneAccessLine(CapturedOutput output) throws Exception {
        track("DKR100000001IN", "access-log-0001");
        mvc.perform(get("/shipment/typo").header("X-Request-Id", "access-log-0002"));
        assertThat(output.getOut())
                .containsPattern("INFO \\[rid:access-log-0001\\] .* GET /shipments/DKR100000001IN -> 200 in \\d+ ms")
                .containsPattern("INFO \\[rid:access-log-0002\\] .* GET /shipment/typo -> 404 in \\d+ ms");
    }
}
