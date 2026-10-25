package com.taskloom.crm;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.function.Supplier;

/**
 * Runs work in a transaction that the database knows belongs to one tenant: as crm_app (so the row-level policy
 * applies, even when the connection itself is a superuser's) and with app.tenant set. Both are LOCAL: they end with the
 * transaction, so a pooled connection never carries one tenant into the next request.
 */
@Component
class TenantScope {

    private final JdbcClient jdbc;
    private final TransactionTemplate tx;

    TenantScope(JdbcClient jdbc, TransactionTemplate tx) {
        this.jdbc = jdbc;
        this.tx = tx;
    }

    <T> T run(String tenant, Supplier<T> work) {
        return tx.execute(status -> {
            jdbc.sql("SET LOCAL ROLE crm_app").update();
            jdbc.sql("SELECT set_config('app.tenant', ?, true)").param(tenant).query().singleValue();
            return work.get();
        });
    }
}
