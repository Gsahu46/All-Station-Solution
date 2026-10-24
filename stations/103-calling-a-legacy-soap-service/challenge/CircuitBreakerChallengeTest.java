package com.bimaly.policies;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static com.bimaly.policies.TestInsurer.INSURER;
import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a struggling 15-year-old system should not get more traffic. After 3 failures in a row (Server faults,
 * timeouts, no connection), stop calling the insurer for bimaly.insurer.cool-down (1 s here) and answer 503 at once.
 * A refusal (Client fault) is the insurer working, not failing.
 */
@TestPropertySource(properties = "bimaly.insurer.cool-down=1s")
class CircuitBreakerChallengeTest extends ApiTest {

    @Test
    void afterThreeFailuresTheInsurerIsLeftAloneForAWhile() throws Exception {
        INSURER.broken = true;
        for (int i = 0; i < 3; i++) {
            issue("TERM10", 1_000_000_000L).andExpect(status().isBadGateway());
        }
        issue("TERM10", 1_000_000_000L).andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.detail").value("The insurer is having trouble. Try again in a minute."));
        assertThat(INSURER.calls).hasSize(3);   // the fourth never reached it

        INSURER.broken = false;
        await().atMost(java.time.Duration.ofSeconds(3)).until(() -> issue("TERM10", 1_000_000_000L).andReturn().getResponse().getStatus() == 201);
    }

    @Test
    void refusalsDoNotOpenTheCircuit() throws Exception {
        for (int i = 0; i < 4; i++) {
            issue("CAR1", 1_000_000_000L).andExpect(status().isUnprocessableContent());
        }
        issue("TERM10", 1_000_000_000L).andExpect(status().isCreated());
    }
}
