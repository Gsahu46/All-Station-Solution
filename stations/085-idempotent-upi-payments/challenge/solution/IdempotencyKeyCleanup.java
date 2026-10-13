package com.paysetu.payments;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.sql.Timestamp;
import java.time.Duration;
import java.time.Instant;

/** SOLUTION to challenge 1. Try it yourself first. */
@Component
@EnableScheduling
public class IdempotencyKeyCleanup {

    private static final Duration RETENTION = Duration.ofHours(24);

    private final JdbcClient jdbc;

    IdempotencyKeyCleanup(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Uses the created_at index from V1, so it does not scan the whole table. */
    public int deleteKeysOlderThan(Duration age) {
        return jdbc.sql("DELETE FROM idempotency_keys WHERE created_at < ?")
                .param(Timestamp.from(Instant.now().minus(age)))
                .update();
    }

    @Scheduled(cron = "0 15 3 * * *") // 03:15 every night, when traffic is lowest
    void nightly() {
        deleteKeysOlderThan(RETENTION);
    }
}
