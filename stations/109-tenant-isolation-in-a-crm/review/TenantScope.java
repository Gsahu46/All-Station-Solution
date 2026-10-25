package com.taskloom.crm;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.function.Supplier;

/**
 * Runs work in a transaction with app.tenant set. Switching roles is not needed: every query in Leads already says
 * WHERE tenant_id = :tenant.
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
            jdbc.sql("SELECT set_config('app.tenant', ?, true)").param(tenant).query().singleValue();
            return work.get();
        });
    }
}
