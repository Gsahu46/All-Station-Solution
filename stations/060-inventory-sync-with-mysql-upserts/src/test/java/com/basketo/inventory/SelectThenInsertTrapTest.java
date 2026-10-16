package com.basketo.inventory;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old nightly sync, step by step on two real MySQL connections (two warehouses' sync jobs), in the
 * order that broke it. Plain JDBC, so every statement and every lock is visible.
 */
class SelectThenInsertTrapTest extends ApiTest {

    @Autowired
    DataSource dataSource;

    @AfterEach
    void dropOldTables() {
        jdbc.sql("DROP TABLE IF EXISTS old_stock_v1, old_stock_v2").update();
    }

    private static void insert(Connection c, String table, long warehouse, String sku, int quantity) throws SQLException {
        try (PreparedStatement insert = c.prepareStatement("INSERT INTO " + table + " (warehouse_id, sku, quantity) VALUES (?, ?, ?)")) {
            insert.setLong(1, warehouse);
            insert.setString(2, sku);
            insert.setInt(3, quantity);
            insert.executeUpdate();
        }
    }

    private static boolean nothingFound(Connection c, String table, long warehouse, String sku) throws SQLException {
        try (PreparedStatement select = c.prepareStatement("SELECT id FROM " + table + " WHERE warehouse_id = ? AND sku = ? FOR UPDATE")) {
            select.setLong(1, warehouse);
            select.setString(2, sku);
            try (ResultSet rs = select.executeQuery()) {
                return !rs.next();
            }
        }
    }

    @Test
    void version1WithoutAUniqueKeyInsertsTheSkuTwice() throws Exception {
        jdbc.sql("CREATE TABLE old_stock_v1 (id BIGINT AUTO_INCREMENT PRIMARY KEY, warehouse_id BIGINT NOT NULL, sku VARCHAR(30) NOT NULL, quantity INT NOT NULL)").update();
        try (Connection a = dataSource.getConnection(); Connection b = dataSource.getConnection()) {
            // The sync job retried on a timeout while the first run was still going: both look before either inserts.
            assertThat(countOf(a, "old_stock_v1", 1, "RICE-5KG")).isZero();
            assertThat(countOf(b, "old_stock_v1", 1, "RICE-5KG")).isZero();
            insert(a, "old_stock_v1", 1, "RICE-5KG", 40);
            insert(b, "old_stock_v1", 1, "RICE-5KG", 40);
        }
        assertThat(jdbc.sql("SELECT count(*) FROM old_stock_v1 WHERE sku = 'RICE-5KG'").query(Long.class).single()).isEqualTo(2);
    }

    private static long countOf(Connection c, String table, long warehouse, String sku) throws SQLException {
        try (PreparedStatement select = c.prepareStatement("SELECT count(*) FROM " + table + " WHERE warehouse_id = ? AND sku = ?")) {
            select.setLong(1, warehouse);
            select.setString(2, sku);
            try (ResultSet rs = select.executeQuery()) {
                rs.next();
                return rs.getLong(1);
            }
        }
    }

    @Test
    void version2WithForUpdateDeadlocksTwoWarehouses() throws Exception {
        jdbc.sql("""
                CREATE TABLE old_stock_v2 (id BIGINT AUTO_INCREMENT PRIMARY KEY, warehouse_id BIGINT NOT NULL, sku VARCHAR(30) NOT NULL,
                    quantity INT NOT NULL, CONSTRAINT old_stock_v2_warehouse_sku UNIQUE (warehouse_id, sku))""").update();
        try (Connection a = dataSource.getConnection(); Connection b = dataSource.getConnection()) {
            a.setAutoCommit(false);
            b.setAutoCommit(false);
            // Two different warehouses, two different new SKUs: they never touch the same row.
            assertThat(nothingFound(a, "old_stock_v2", 1, "RICE-5KG")).isTrue();   // locks the gap where the row would go
            assertThat(nothingFound(b, "old_stock_v2", 2, "ATTA-10KG")).isTrue();  // the same gap: gap locks do not block each other
            List<String> outcomes = together(2, i -> i == 0
                    ? commitAfter(a, () -> insert(a, "old_stock_v2", 1, "RICE-5KG", 40))     // waits for b's gap lock
                    : commitAfter(b, () -> insert(b, "old_stock_v2", 2, "ATTA-10KG", 12)));  // waits for a's: a cycle
            assertThat(outcomes).containsExactlyInAnyOrder("committed", "1213 Deadlock found when trying to get lock; try restarting transaction");
        }
    }

    @Test
    void theUpsertGivesBothWarehousesTheirRowWithoutLookingFirst() throws Exception {
        String upsert = "INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES (?, ?, ?) AS incoming ON DUPLICATE KEY UPDATE quantity = incoming.quantity";
        try (Connection a = dataSource.getConnection(); Connection b = dataSource.getConnection()) {
            a.setAutoCommit(false);
            b.setAutoCommit(false);
            List<String> outcomes = together(2, i -> i == 0
                    ? commitAfter(a, () -> upsertOne(a, upsert, 1, "RICE-5KG", 40))
                    : commitAfter(b, () -> upsertOne(b, upsert, 2, "ATTA-10KG", 12)));
            assertThat(outcomes).containsOnly("committed");
            // And the retried job from version 1: the second run finds the key taken and updates instead.
            upsertOne(a, upsert, 1, "RICE-5KG", 40);
            a.commit();
        }
        assertThat(rows(1)).isEqualTo(1);
        assertThat(rows(2)).isEqualTo(1);
    }

    private static void upsertOne(Connection c, String sql, long warehouse, String sku, int quantity) throws SQLException {
        try (PreparedStatement upsert = c.prepareStatement(sql)) {
            upsert.setLong(1, warehouse);
            upsert.setString(2, sku);
            upsert.setInt(3, quantity);
            upsert.executeUpdate();
        }
    }

    interface Step {
        void run() throws SQLException;
    }

    private static String commitAfter(Connection c, Step step) throws SQLException {
        try {
            step.run();
            c.commit();
            return "committed";
        } catch (SQLException e) {
            c.rollback();
            return e.getErrorCode() + " " + e.getMessage();
        }
    }
}
