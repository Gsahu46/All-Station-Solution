package com.mediqo.pharmacy;

import com.zaxxer.hikari.HikariDataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.sql.SQLException;
import java.sql.SQLTransientConnectionException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The first test written for this station: the old search, run against the real database. */
class ConcatenatedSqlTrapTest extends ApiTest {

    /** 12 characters: a length limit on the search box is not a defence. */
    static final String ALWAYS_TRUE = "x' OR 1=1 --";
    static final String DUMP_PRESCRIPTIONS = "x' UNION SELECT patient_name, patient_phone, doctor FROM prescriptions --";

    @Autowired
    MedicineSearch search;

    /** A pool of its own, so the leak cannot starve the other tests: 3 connections, give up after 250 ms. */
    HikariDataSource smallPool() {
        HikariDataSource app = (HikariDataSource) dataSource;
        HikariDataSource pool = new HikariDataSource();
        pool.setJdbcUrl(app.getJdbcUrl());
        pool.setUsername(app.getUsername());
        pool.setPassword(app.getPassword());
        pool.setMaximumPoolSize(3);
        pool.setConnectionTimeout(250);
        return pool;
    }

    @Test
    void theOldSearchHandsOverEveryPrescription() throws SQLException {
        try (HikariDataSource pool = smallPool()) {
            assertThat(OldMedicineSearch.byName(pool, DUMP_PRESCRIPTIONS))
                    .contains("Asha Verma | 90000 00001 | Dr Mehta", "Ravi Iyer | 90000 00002 | Dr Rao", "Fatima Shaikh | 90000 00003 | Dr Mehta");
        }
        assertThat(search.byName(DUMP_PRESCRIPTIONS)).isEmpty();   // just text to the fixed query: no medicine has that name
    }

    @Test
    void aShortPayloadFitsTheLengthLimitAndStillGetsEverything() throws SQLException {
        try (HikariDataSource pool = smallPool()) {
            assertThat(OldMedicineSearch.byName(pool, ALWAYS_TRUE)).hasSize(15);   // every medicine, whatever was typed
        }
        assertThat(search.byName(ALWAYS_TRUE)).isEmpty();
    }

    @Test
    void theOldSearchBreaksOnAnApostrophe() throws SQLException {
        try (HikariDataSource pool = smallPool()) {
            assertThatThrownBy(() -> OldMedicineSearch.byName(pool, "john's")).isInstanceOf(SQLException.class).hasMessageContaining("Unterminated string literal");
        }
        assertThat(search.byName("john's")).extracting(Medicine::name).containsExactly("St. John's Wort");
    }

    @Test
    void theOldSearchLeaksAConnectionEveryTime() throws SQLException {
        try (HikariDataSource pool = smallPool()) {
            for (int i = 0; i < 3; i++) {
                OldMedicineSearch.byName(pool, "para");
            }
            assertThat(pool.getHikariPoolMXBean().getActiveConnections()).isEqualTo(3);   // all taken, none returned
            assertThatThrownBy(() -> OldMedicineSearch.byName(pool, "para"))
                    .isInstanceOf(SQLTransientConnectionException.class).hasMessageContaining("request timed out");
        }
    }

    @Test
    void theRealSearchGivesEveryConnectionBack() throws Exception {
        for (int i = 0; i < 50; i++) {
            search("para");
        }
        assertThat(((HikariDataSource) dataSource).getHikariPoolMXBean().getActiveConnections()).isZero();
    }
}
