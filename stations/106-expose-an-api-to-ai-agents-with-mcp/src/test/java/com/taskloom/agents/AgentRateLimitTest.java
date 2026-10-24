package com.taskloom.agents;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;

/** 5 requests a minute per caller here (60 in production). */
@TestPropertySource(properties = "taskloom.agents.requests-per-minute=5")
class AgentRateLimitTest extends ApiTest {

    @Test
    void anAgentInALoopIsStoppedWith429AndOthersAreNot() throws Exception {
        if (java.time.LocalTime.now().getSecond() > 50) {
            Thread.sleep((61 - java.time.LocalTime.now().getSecond()) * 1000L);   // the counts are per clock minute: start in a fresh one
        }
        int ok = 0;
        java.net.http.HttpResponse<String> last = null;
        for (int i = 0; i < 8; i++) {
            last = rawPost(INITIALIZE, "Authorization", "Bearer " + WRITER);
            ok += last.statusCode() == 200 ? 1 : 0;
        }
        assertThat(ok).isEqualTo(5);
        assertThat(last.statusCode()).isEqualTo(429);
        assertThat(Integer.parseInt(last.headers().firstValue("Retry-After").orElseThrow())).isBetween(1, 60);
        assertThat(rawPost(INITIALIZE, "Authorization", "Bearer " + STUDIO).statusCode()).as("another caller").isEqualTo(200);
    }
}
