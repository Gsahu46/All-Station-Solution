package com.taskloom.crm;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The isolation rule in the database itself: plain SQL, as crm_app, no Java filters. */
class LeadDatabaseTest extends ApiTest {

    @Autowired
    TenantScope scope;
    @Autowired
    TransactionTemplate tx;

    int countAsApp(String tenantOrNull) {
        return tx.execute(s -> {
            jdbc.sql("SET LOCAL ROLE crm_app").update();
            if (tenantOrNull != null) {
                jdbc.sql("SELECT set_config('app.tenant', ?, true)").param(tenantOrNull).query().singleValue();
            }
            return jdbc.sql("SELECT count(*) FROM leads").query(Integer.class).single();   // no WHERE at all
        });
    }

    @Test
    void thePolicyShowsAndWritesOnlyTheTransactionsTenant() {
        assertThat(countAsApp("zestful")).isEqualTo(2);
        assertThat(countAsApp("brightpath")).isEqualTo(2);
        assertThat(countAsApp(null)).as("no tenant set, no rows").isZero();
        assertThat(countAsApp("nobody")).isZero();

        assertThatThrownBy(() -> scope.run("zestful", () -> jdbc.sql(
                        "INSERT INTO leads (tenant_id, name, email, owner) VALUES ('brightpath', 'X', 'x@example.com', 'ananya')").update()))
                .rootCause().hasMessageContaining("violates row-level security policy");   // Spring wraps it as "bad SQL grammar"
        int updated = scope.run("zestful", () -> jdbc.sql("UPDATE leads SET status = 'LOST' WHERE email = 'sunil.rao@example.org'").update());
        assertThat(updated).as("Brightpath's lead is invisible to Zestful's UPDATE").isZero();
        assertThatThrownBy(() -> scope.run("zestful", () -> jdbc.sql("DELETE FROM leads").update()))
                .rootCause().hasMessageContaining("permission denied");   // crm_app was never granted DELETE
    }

    @Test
    void theRulesAreNamedConstraints() {
        assertThatThrownBy(() -> scope.run("zestful", () -> jdbc.sql(
                        "INSERT INTO leads (tenant_id, name, email, owner) VALUES ('zestful', 'X', 'rahul@spicehub.example', 'ananya')").update()))
                .hasMessageContaining("leads_email_unique_per_tenant");
        assertThatThrownBy(() -> scope.run("zestful", () -> jdbc.sql(
                        "INSERT INTO leads (tenant_id, name, email, status, owner) VALUES ('zestful', 'X', 'y@example.com', 'WON', 'ananya')").update()))
                .hasMessageContaining("leads_status");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO tenants (id, name) VALUES ('Bad Tenant', 'x')").update())
                .hasMessageContaining("tenants_id_format");
    }

    @Test
    void theTenantEndsWithItsTransactionAndAFailedWriteLeavesNothing() {
        assertThatThrownBy(() -> scope.run("zestful", () -> {
            jdbc.sql("INSERT INTO leads (tenant_id, name, email, owner) VALUES ('zestful', 'A', 'a@example.com', 'ananya')").update();
            return jdbc.sql("INSERT INTO leads (tenant_id, name, email, owner) VALUES ('zestful', 'B', 'a@example.com', 'ananya')").update();
        })).hasMessageContaining("leads_email_unique_per_tenant");
        assertThat(tenantOf("a@example.com")).as("rolled back").isEmpty();
        // The same pooled connections, a new transaction with nothing set: the last tenant did not stay behind.
        for (int i = 0; i < 12; i++) {
            assertThat(countAsApp(null)).isZero();
        }
    }
}
