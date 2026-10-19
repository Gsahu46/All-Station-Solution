package com.fitnest.workouts;

import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Token ids that logged out, each kept only until the token would have expired anyway. */
@Component
class RevokedTokens {

    // shortcut: one pod's memory, so other pods still accept the token; with several pods keep this in Valkey or a table.
    private final Map<String, Instant> revoked = new ConcurrentHashMap<>();
    private final Clock clock;

    RevokedTokens(Clock clock) {
        this.clock = clock;
    }

    void revoke(String id, Instant expiresAt) {
        revoked.put(id, expiresAt);
    }

    boolean isRevoked(String id) {
        Instant now = clock.instant();
        revoked.values().removeIf(expires -> expires.isBefore(now));
        return id != null && revoked.containsKey(id);
    }
}
