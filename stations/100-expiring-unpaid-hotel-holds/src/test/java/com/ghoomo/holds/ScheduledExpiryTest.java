package com.ghoomo.holds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;

import java.time.Duration;
import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/** The real schedule and clock: a hold of 1 s, a check every 200 ms, and nobody calls the job. */
@SpringBootTest(properties = {"ghoomo.holds.ttl=1s", "ghoomo.holds.expiry.every=200ms"})
@Import(PostgresTestConfig.class)
class ScheduledExpiryTest {

    @Autowired
    Holds holds;

    @Test
    void anUnpaidHoldExpiresOnItsOwn() {
        long id = holds.create("scheduled-0001", 1, LocalDate.parse("2026-12-31"), "asha@example.com").hold().id();
        await().atMost(Duration.ofSeconds(5)).until(() -> holds.find(id).orElseThrow().status().equals("EXPIRED"));
        assertThat(holds.find(id).orElseThrow().status()).isEqualTo("EXPIRED");
    }
}
