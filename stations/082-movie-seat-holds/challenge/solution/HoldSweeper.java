package com.seatsure.holds;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;

@Component
class HoldSweeper {

    private final JdbcClient jdbc;
    private final Clock clock;

    HoldSweeper(JdbcClient jdbc, Clock clock) {
        this.jdbc = jdbc;
        this.clock = clock;
    }

    /** One batch. SKIP LOCKED: a hold another sweeper has already picked is left to it. */
    @Transactional
    int sweep(int batchSize) {
        OffsetDateTime now = OffsetDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
        List<UUID> expired = jdbc.sql("SELECT id FROM holds WHERE status = 'held' AND expires_at <= ? ORDER BY expires_at LIMIT ? FOR UPDATE SKIP LOCKED")
                .params(now, batchSize).query(UUID.class).list();
        for (UUID id : expired) {
            jdbc.sql("UPDATE seats SET hold_id = NULL, held_until = NULL WHERE hold_id = ?").param(id).update();
            jdbc.sql("UPDATE holds SET status = 'expired' WHERE id = ?").param(id).update();
        }
        return expired.size();
    }
}
