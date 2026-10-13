package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * CHALLENGE 1: keys must not live forever.
 * Copy this file into src/test/java/com/paysetu/payments/ and make it pass.
 * You need a Spring bean IdempotencyKeyCleanup with: int deleteKeysOlderThan(Duration age)
 */
class KeyCleanupChallengeTest extends ApiTest {

    @Autowired
    IdempotencyKeyCleanup cleanup;

    @Test
    void deletesOnlyKeysOlderThanTheRetentionWindow() {
        pay("old-key-000001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("new-key-000001", ASHA_PAYS_RAVI.replace("12550", "500")).expectStatus().isCreated();
        ageKey("old-key-000001", 25);

        int deleted = cleanup.deleteKeysOlderThan(Duration.ofHours(24));

        assertThat(deleted).isEqualTo(1);
        assertThat(jdbc.sql("SELECT idem_key FROM idempotency_keys").query(String.class).list())
                .containsExactly("new-key-000001");
        assertThat(paymentCount()).as("payments are records; only keys expire").isEqualTo(2);
    }

    @Test
    void aRetryAfterCleanupIsTreatedAsANewPayment() {
        pay("late-retry-0001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        ageKey("late-retry-0001", 25);
        cleanup.deleteKeysOlderThan(Duration.ofHours(24));

        pay("late-retry-0001", ASHA_PAYS_RAVI)
                .expectStatus().isCreated()
                .expectHeader().valueEquals("Idempotent-Replayed", "false");
        // This is why retention must be longer than the longest client retry window.
        assertThat(paymentCount()).isEqualTo(2);
    }

    private void ageKey(String key, int hours) {
        jdbc.sql("UPDATE idempotency_keys SET created_at = now() - make_interval(hours => ?) WHERE idem_key = ?")
                .params(hours, key)
                .update();
    }
}
