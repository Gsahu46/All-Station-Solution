package com.paysetu.payments;

import io.micrometer.core.instrument.MeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * CHALLENGE 2: make retries visible to the on-call engineer.
 * Copy this file into src/test/java/com/paysetu/payments/ and make it pass.
 * Count two things with Micrometer:
 *   paysetu.payments.replayed    - a stored response was returned
 *   paysetu.payments.key_reused  - a key came back with a different body (422)
 * Hint: add spring-boot-starter-actuator to pom.xml to get a MeterRegistry.
 */
class ReplayMetricsChallengeTest extends ApiTest {

    @Autowired
    MeterRegistry meters;

    @Test
    void countsReplaysAndKeyReuse() {
        double replayedBefore = count("paysetu.payments.replayed");
        double reusedBefore = count("paysetu.payments.key_reused");

        pay("metrics-key-001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("metrics-key-001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("metrics-key-001", ASHA_PAYS_RAVI.replace("12550", "99900")).expectStatus().isEqualTo(422);

        assertThat(count("paysetu.payments.replayed") - replayedBefore).isEqualTo(1);
        assertThat(count("paysetu.payments.key_reused") - reusedBefore).isEqualTo(1);
    }

    private double count(String name) {
        return meters.counter(name).count();
    }
}
