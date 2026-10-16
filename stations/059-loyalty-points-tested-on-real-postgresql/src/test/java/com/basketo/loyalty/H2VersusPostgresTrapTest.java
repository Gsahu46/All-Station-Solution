package com.basketo.loyalty;

import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The first test written for this station. The old upsert, from the code that shipped, run on the in-memory H2 the
 * old tests used (even in its PostgreSQL compatibility mode it accepts H2's own syntax), and on the real PostgreSQL
 * production runs.
 */
class H2VersusPostgresTrapTest extends ApiTest {

    /** H2's own MERGE syntax (a column list and a KEY clause): not SQL standard, not PostgreSQL. */
    static final String OLD_UPSERT = "MERGE INTO point_balances (customer_id, points) KEY (customer_id) VALUES (?, ?)";

    static final String NEW_UPSERT = """
            INSERT INTO point_balances (customer_id, points) VALUES (?, ?)
            ON CONFLICT (customer_id) DO UPDATE SET points = point_balances.points + EXCLUDED.points RETURNING points""";

    static Connection h2() throws SQLException {
        Connection c = DriverManager.getConnection("jdbc:h2:mem:old-tests;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE");
        try (Statement s = c.createStatement()) {
            s.execute("CREATE TABLE IF NOT EXISTS point_balances (customer_id BIGINT PRIMARY KEY, points INT NOT NULL)");
        }
        return c;
    }

    @Test
    void theOldUpsertRunsOnH2() throws SQLException {
        try (Connection c = h2(); var merge = c.prepareStatement(OLD_UPSERT)) {
            merge.setLong(1, 7);
            merge.setInt(2, 14);
            assertThat(merge.executeUpdate()).isEqualTo(1);   // green on H2: the old test suite passed
        }
    }

    @Test
    void andPostgresqlRejectsIt() {
        long customer = newCustomer();
        // PostgreSQL has a standard MERGE (MERGE INTO t USING ...), so it stops at the column list H2 allowed.
        assertThatThrownBy(() -> jdbc.sql(OLD_UPSERT).params(customer, 14).update())
                .rootCause().hasMessageContaining("syntax error at or near \"(\"");   // the first production earn after the release
    }

    @Test
    void theRightSqlForPostgresqlIsNotH2Sql() throws SQLException {
        try (Connection c = h2()) {
            assertThatThrownBy(() -> c.prepareStatement(NEW_UPSERT)).isInstanceOf(SQLException.class)
                    .hasMessageContaining("Syntax error");   // H2 cannot even parse it: it can only be tested on PostgreSQL
        }
        long customer = newCustomer();
        assertThat(jdbc.sql(NEW_UPSERT).params(customer, 14).query(Integer.class).single()).isEqualTo(14);
    }
}
