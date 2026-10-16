package com.taskloom.signups;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The first test written for this station, without Spring: the old table, "email VARCHAR(254) UNIQUE", created the
 * same way on both real databases, and the same two inserts. The databases disagree.
 */
class CaseSensitivityTrapTest {

    static final String OLD_TABLE = "CREATE TABLE old_signups (id INT PRIMARY KEY, email VARCHAR(254) NOT NULL UNIQUE)";

    @BeforeAll
    static void start() {
        Databases.POSTGRES.start();
        Databases.MYSQL.start();
    }

    /** The containers are shared with the Spring tests, whose Flyway wants an empty schema: leave none behind. */
    @AfterAll
    static void dropTheOldTable() throws SQLException {
        for (var db : java.util.List.of(Databases.POSTGRES, Databases.MYSQL)) {
            try (Connection c = open(db); Statement s = c.createStatement()) {
                s.execute("DROP TABLE IF EXISTS old_signups");
            }
        }
    }

    static Connection open(org.testcontainers.containers.JdbcDatabaseContainer<?> db) throws SQLException {
        return DriverManager.getConnection(db.getJdbcUrl(), db.getUsername(), db.getPassword());
    }

    /** Creates the old table fresh and inserts the emails in order; returns how many rows went in before one was refused. */
    static int insert(org.testcontainers.containers.JdbcDatabaseContainer<?> db, String... emails) throws SQLException {
        try (Connection c = open(db); Statement s = c.createStatement()) {
            s.execute("DROP TABLE IF EXISTS old_signups");
            s.execute(OLD_TABLE);
            for (int i = 0; i < emails.length; i++) {
                try {
                    s.execute("INSERT INTO old_signups VALUES (" + i + ", '" + emails[i] + "')");
                } catch (SQLException duplicate) {
                    return i;
                }
            }
            return emails.length;
        }
    }

    @Test
    void postgresqlKeepsTwoAshas() throws SQLException {
        assertThat(insert(Databases.POSTGRES, "Asha@x.com", "asha@x.com")).isEqualTo(2);   // two accounts for one person
    }

    @Test
    void mysqlKeepsOne() throws SQLException {
        assertThat(insert(Databases.MYSQL, "Asha@x.com", "asha@x.com")).isEqualTo(1);      // its default collation ignores case
    }

    @Test
    void mysqlAlsoIgnoresAccentsWhichNobodyAskedFor() throws SQLException {
        // utf8mb4_0900_ai_ci: "ai" is accent-insensitive. Two different addresses collide.
        assertThat(insert(Databases.MYSQL, "jose@x.com", "josé@x.com")).isEqualTo(1);
        assertThat(insert(Databases.POSTGRES, "jose@x.com", "josé@x.com")).isEqualTo(2);
    }

    @Test
    void theOldCodeLookedUpWithEqualsSoPostgresMissedTheDuplicateToo() throws SQLException {
        insert(Databases.POSTGRES, "Asha@x.com");
        try (Connection c = open(Databases.POSTGRES); Statement s = c.createStatement()) {
            var found = s.executeQuery("SELECT count(*) FROM old_signups WHERE email = 'asha@x.com'");
            found.next();
            assertThat(found.getInt(1)).isZero();   // "not signed up yet", says the check before the insert
        }
        assertThatThrownBy(() -> {
            try (Connection c = open(Databases.POSTGRES); Statement s = c.createStatement()) {
                s.execute("CREATE UNIQUE INDEX old_signups_lower ON old_signups (lower(email))");
                s.execute("INSERT INTO old_signups VALUES (9, 'asha@x.com')");
            }
        }).hasMessageContaining("old_signups_lower");   // the fix, on the same table: now refused
    }
}
