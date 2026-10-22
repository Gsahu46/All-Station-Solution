package com.tijori.wallets;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old code summed today's top-ups and, if the new one fitted, inserted it, with no lock. Two
 * top-ups of ₹6,000 at the same second each summed ₹0 and both went in: ₹12,000 on a ₹10,000 limit. These tests
 * drive two real transactions step by step, so the bad order happens every time.
 */
class UnlockedSumTrapTest extends ApiTest {

    @Autowired
    DataSource dataSource;

    Connection begin() throws SQLException {
        Connection c = dataSource.getConnection();
        c.setAutoCommit(false);
        return c;   // READ COMMITTED, the default
    }

    static long sumToday(Connection c) throws SQLException {
        try (var rs = c.createStatement().executeQuery("SELECT coalesce(sum(amount_paise), 0) FROM top_ups WHERE wallet_id = 1001")) {
            rs.next();
            return rs.getLong(1);
        }
    }

    static void lockWallet(Connection c) throws SQLException {
        c.createStatement().execute("SELECT id FROM wallets WHERE id = 1001 FOR UPDATE");
    }

    static void insert(Connection c, long paise) throws SQLException {
        try (PreparedStatement s = c.prepareStatement("INSERT INTO top_ups (wallet_id, amount_paise) VALUES (1001, ?)")) {
            s.setLong(1, paise);
            s.executeUpdate();
        }
    }

    @Test
    void withoutALockBothTopUpsSawNothingAndBothWentIn() throws Exception {
        jdbc.sql("ALTER TABLE top_ups DISABLE TRIGGER top_ups_within_daily_limit").update();   // the old schema had no such rule
        try (Connection first = begin(); Connection second = begin()) {
            assertThat(sumToday(first)).isZero();    // "₹0 so far, ₹6,000 fits"
            assertThat(sumToday(second)).isZero();   // "₹0 so far, ₹6,000 fits"
            insert(first, 600000);
            insert(second, 600000);                  // a new row: there was nothing to wait for
            first.commit();
            second.commit();
        } finally {
            jdbc.sql("ALTER TABLE top_ups ENABLE TRIGGER top_ups_within_daily_limit").update();
        }
        assertThat(toppedUp(ANANYA)).isEqualTo(1200000);
    }

    @Test
    void withTheWalletLockedTheSecondWaitsAndThenSeesTheFirst() throws Exception {
        jdbc.sql("ALTER TABLE top_ups DISABLE TRIGGER top_ups_within_daily_limit").update();   // only the application's lock is tested here
        try (Connection first = begin(); Connection second = begin()) {
            lockWallet(first);
            assertThat(sumToday(first)).isZero();
            CompletableFuture<Long> secondSum = CompletableFuture.supplyAsync(() -> {
                try {
                    lockWallet(second);              // waits for the first transaction
                    return sumToday(second);
                } catch (SQLException e) {
                    throw new IllegalStateException(e);
                }
            });
            Thread.sleep(300);
            assertThat(secondSum).isNotDone();
            insert(first, 600000);
            first.commit();
            assertThat(secondSum.get()).isEqualTo(600000);   // ₹6,000 already: another ₹6,000 does not fit
            second.rollback();
        } finally {
            jdbc.sql("ALTER TABLE top_ups ENABLE TRIGGER top_ups_within_daily_limit").update();
        }
        assertThat(toppedUp(ANANYA)).isEqualTo(600000);
    }
}
