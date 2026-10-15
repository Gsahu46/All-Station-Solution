package com.fitnest.members;

import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The first test written for this station. Schema "v1_only" holds the database as version 1 shipped (rules in Java
 * only); another writer, here plain SQL, stores what the Java code would have refused. The app's schema, at version 2,
 * refuses the same rows by name.
 */
class JavaOnlyRulesTrapTest extends ApiTest {

    @BeforeEach
    void versionOneInItsOwnSchema() {
        jdbc.sql("DROP SCHEMA IF EXISTS v1_only CASCADE").update();
        Flyway.configure().dataSource(dataSource).schemas("v1_only").target("1").load().migrate();
    }

    @Test
    void versionOneLetsAnotherWriterStoreTwoMembersWithOnePhone() {
        jdbc.sql("INSERT INTO v1_only.members (name, phone) VALUES ('Asha Verma', '98765 43210'), ('Asha V', '+91 9876543210')").update();
        assertThat(jdbc.sql("SELECT count(*) FROM v1_only.members").query(Long.class).single()).isEqualTo(2);

        jdbc.sql("INSERT INTO members (name, phone) VALUES ('Asha Verma', '9876543210')").update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO members (name, phone) VALUES ('Asha V', '9876543210')").update())
                .hasMessageContaining("members_phone_unique");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO members (name, phone) VALUES ('Asha V', '+91 9876543210')").update())
                .hasMessageContaining("members_phone_digits");   // only the one stored form is allowed, so UNIQUE can see duplicates
    }

    @Test
    void versionOneLetsAMembershipEndBeforeItStarts() {
        jdbc.sql("INSERT INTO v1_only.memberships (member_id, plan, starts_on, ends_on, price_paise) VALUES (1, 'Monthly', DATE '2026-11-01', DATE '2026-10-01', 149900)").update();
        assertThat(jdbc.sql("SELECT count(*) FROM v1_only.memberships WHERE ends_on < starts_on").query(Long.class).single()).isEqualTo(1);

        long member = jdbc.sql("INSERT INTO members (name, phone) VALUES ('Ravi Iyer', '9123456780') RETURNING id").query(Long.class).single();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO memberships (member_id, plan_code, starts_on, ends_on, price_paise) VALUES (?, 'MONTHLY', DATE '2026-11-01', DATE '2026-10-01', 149900)")
                .param(member).update())
                .hasMessageContaining("memberships_dates_order");
    }
}
