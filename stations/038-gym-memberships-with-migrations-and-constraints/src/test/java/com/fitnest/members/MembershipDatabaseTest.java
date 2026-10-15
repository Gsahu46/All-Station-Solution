package com.fitnest.members;

import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.FlywayException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Every rule as a named constraint, tested with plain SQL; a rollback; and a migration meeting bad data. */
class MembershipDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    long member(String phone) {
        return jdbc.sql("INSERT INTO members (name, phone) VALUES ('Test', ?) RETURNING id").param(phone).query(Long.class).single();
    }

    void membership(long member, String plan, String starts, String ends, long paise) {
        jdbc.sql("INSERT INTO memberships (member_id, plan_code, starts_on, ends_on, price_paise) VALUES (?, ?, ?::date, ?::date, ?)")
                .params(member, plan, starts, ends, paise).update();
    }

    @Test
    void everyRuleIsANamedConstraint() {
        long asha = member("9876543210");
        assertThatThrownBy(() -> member("12345")).hasMessageContaining("members_phone_digits");
        assertThatThrownBy(() -> membership(999, "MONTHLY", "2026-11-01", "2026-11-30", 149900)).hasMessageContaining("memberships_member_fk");
        assertThatThrownBy(() -> membership(asha, "WEEKLY", "2026-11-01", "2026-11-07", 49900)).hasMessageContaining("memberships_plan_fk");
        assertThatThrownBy(() -> membership(asha, "MONTHLY", "2026-11-01", "2026-11-30", 0)).hasMessageContaining("memberships_price_positive");
    }

    @Test
    void overlappingMembershipsAreRefusedButBackToBackOnesAreFine() {
        long asha = member("9876543210");
        membership(asha, "MONTHLY", "2026-11-01", "2026-11-30", 149900);
        assertThatThrownBy(() -> membership(asha, "MONTHLY", "2026-11-30", "2026-12-29", 149900)).hasMessageContaining("memberships_no_overlap");
        membership(asha, "MONTHLY", "2026-12-01", "2026-12-31", 149900);   // starts the day after the last one ends
        membership(member("9123456780"), "MONTHLY", "2026-11-01", "2026-11-30", 149900);   // another member, same days
        assertThat(count("memberships")).isEqualTo(3);
    }

    @Test
    void aFailureInsideATransactionTakesTheNewMemberWithIt() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(status -> {
            long ravi = member("9123456780");
            membership(ravi, "MONTHLY", "2026-11-30", "2026-11-01", 149900);   // refused: ends before it starts
        })).hasMessageContaining("memberships_dates_order");
        assertThat(count("members")).isZero();
    }

    @Test
    void addingConstraintsToBadDataFailsTheMigrationUntilTheDataIsFixed() {
        jdbc.sql("DROP SCHEMA IF EXISTS legacy CASCADE").update();
        Flyway v1 = Flyway.configure().dataSource(dataSource).schemas("legacy").target("1").load();
        v1.migrate();
        jdbc.sql("INSERT INTO legacy.members (name, phone) VALUES ('Asha Verma', '98765 43210'), ('Asha V', '+91 9876543210')").update();
        jdbc.sql("INSERT INTO legacy.memberships (member_id, plan, starts_on, ends_on, price_paise) VALUES (1, 'Monthly ', DATE '2026-11-01', DATE '2026-10-01', 149900)").update();
        Flyway latest = Flyway.configure().dataSource(dataSource).schemas("legacy").load();

        assertThatThrownBy(latest::migrate).isInstanceOf(FlywayException.class).hasMessageContaining("members_phone_unique");
        assertThat(jdbc.sql("SELECT phone FROM legacy.members ORDER BY id").query(String.class).list())
                .containsExactly("98765 43210", "+91 9876543210");   // the whole of V2 was rolled back, even its UPDATE

        jdbc.sql("DELETE FROM legacy.members WHERE id = 2").update();   // the duplicate, after checking with the gym
        assertThatThrownBy(latest::migrate).isInstanceOf(FlywayException.class).hasMessageContaining("memberships_dates_order");

        jdbc.sql("UPDATE legacy.memberships SET ends_on = DATE '2026-11-30' WHERE id = 1").update();
        latest.migrate();
        assertThat(jdbc.sql("SELECT plan_code FROM legacy.memberships").query(String.class).single()).isEqualTo("MONTHLY");
        assertThat(jdbc.sql("SELECT phone FROM legacy.members").query(String.class).single()).isEqualTo("9876543210");
    }

    @Test
    void theAppsSchemaHasBothVersionsInOrder() {
        assertThat(jdbc.sql("SELECT version FROM flyway_schema_history WHERE success ORDER BY installed_rank").query(String.class).list())
                .startsWith("1", "2");
    }
}
