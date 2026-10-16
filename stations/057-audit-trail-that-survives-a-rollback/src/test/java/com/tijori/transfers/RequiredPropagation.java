package com.tijori.transfers;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;

/** Test-only bean: the same audit insert with the default propagation, REQUIRED, for comparison. */
class RequiredPropagation {

    private final JdbcClient jdbc;

    RequiredPropagation(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    public void record() {
        jdbc.sql("INSERT INTO audit_events (attempt_id, event, from_account, to_account, amount_paise) VALUES (gen_random_uuid(), 'TRANSFER_ATTEMPTED', 1, 2, 100)").update();
    }
}
