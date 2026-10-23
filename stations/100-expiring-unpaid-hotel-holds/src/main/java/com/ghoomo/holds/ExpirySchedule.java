package com.ghoomo.holds;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

/**
 * Every 30 s after the last run ended (fixed delay: runs on one server never overlap). It runs on every server;
 * Holds.expireDue makes that safe. Tests switch it off and run it themselves.
 */
@Configuration
@EnableScheduling
@ConditionalOnProperty(name = "ghoomo.holds.expiry.enabled", havingValue = "true", matchIfMissing = true)
class ExpirySchedule {

    private final Holds holds;

    ExpirySchedule(Holds holds) {
        this.holds = holds;
    }

    @Scheduled(fixedDelayString = "${ghoomo.holds.expiry.every}")
    void run() {
        holds.expireDue();
    }
}
