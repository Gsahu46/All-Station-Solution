package com.dakroute.shipments;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules as PostgreSQL enforces them, with plain SQL; and what an index costs every insert. */
class ShipmentDatabaseTest extends ApiTest {

    @AfterEach
    void removeTestRows() {
        jdbc.sql("DELETE FROM shipments WHERE awb LIKE 'DR9%'").update();
        jdbc.sql("DROP TABLE IF EXISTS bare, indexed").update();
    }

    private void insert(String awb, String phone, String status) {
        jdbc.sql("INSERT INTO shipments (awb, phone, booked_on, status) VALUES (?, ?, DATE '2026-06-01', ?)").params(awb, phone, status).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        insert("DR9000000001", "9876543210", "BOOKED");
        assertThatThrownBy(() -> insert("DR9000000001", "9876543210", "BOOKED")).isInstanceOf(DataAccessException.class).hasMessageContaining("shipments_awb_unique");
        assertThatThrownBy(() -> insert("XX9000000002", "9876543210", "BOOKED")).hasMessageContaining("shipments_awb_shape");
        assertThatThrownBy(() -> insert("DR9000000003", "98765-4321", "BOOKED")).hasMessageContaining("shipments_phone_shape");
        assertThatThrownBy(() -> insert("DR9000000004", "9876543210", "LOST")).hasMessageContaining("shipments_status_known");
    }

    @Test
    void aBatchWithOneBadPhoneLeavesNothingBehind() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(status -> {
            insert("DR9000000011", "9876543210", "BOOKED");
            insert("DR9000000012", "9876543210", "BOOKED");
            insert("DR9000000013", "0987654321", "BOOKED");   // typed with the leading 0, not cleaned
        })).hasMessageContaining("shipments_phone_shape");
        assertThat(jdbc.sql("SELECT count(*) FROM shipments WHERE awb LIKE 'DR90000000%'").query(Long.class).single()).isZero();
    }

    @Test
    void everyIndexIsMoreWorkForEveryInsert() {
        jdbc.sql("CREATE TABLE bare (LIKE shipments)").update();
        jdbc.sql("CREATE TABLE indexed (LIKE shipments)").update();
        jdbc.sql("CREATE INDEX indexed_awb ON indexed (awb)").update();
        jdbc.sql("CREATE INDEX indexed_phone_date ON indexed (phone, booked_on)").update();
        jdbc.sql("CREATE INDEX indexed_date_phone ON indexed (booked_on, phone)").update();
        long bare = walRecordsToInsert1000("bare");
        long indexed = walRecordsToInsert1000("indexed");
        assertThat(bare).isBetween(1000L, 1100L);      // one record per row, plus a few for new pages
        assertThat(indexed).isGreaterThan(3 * bare);   // and one more per row for each index
    }

    /** WAL records an insert of 1000 rows writes: every change PostgreSQL must log, rows and index entries alike. */
    private long walRecordsToInsert1000(String table) {
        return transaction.execute(status -> {
            String plan = jdbc.sql("EXPLAIN (ANALYZE, WAL, FORMAT JSON) INSERT INTO " + table
                    + " SELECT id, awb, phone, booked_on, status FROM shipments ORDER BY id LIMIT 1000").query(String.class).single();
            JsonNode root = json.readTree(plan).get(0).get("Plan");
            return root.get("WAL Records").asLong();
        });
    }
}
