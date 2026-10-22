package com.tijori.wallets;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules hold for any writer, not only this API: plain SQL, no Java in between. */
class TopUpDatabaseTest extends ApiTest {

    @Autowired
    DataSource dataSource;

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).hasMessageContaining(constraint);
    }

    @Test
    void theDailyLimitHoldsForEveryWriter() {
        jdbc.sql("INSERT INTO top_ups (wallet_id, amount_paise, created_at) VALUES (1001, 900000, '2026-10-30 23:00+05:30')").update();
        violates("top_ups_within_daily_limit", "INSERT INTO top_ups (wallet_id, amount_paise, created_at) VALUES (1001, 200000, '2026-10-30 08:00+05:30')");
        jdbc.sql("INSERT INTO top_ups (wallet_id, amount_paise, created_at) VALUES (1001, 200000, '2026-10-31 00:00+05:30')").update();   // the next IST day
        assertThat(toppedUp(ANANYA)).isEqualTo(1100000);
    }

    @Test
    void theDailyLimitHoldsForTwoPlainSqlWritersAtOnce() throws Exception {
        try (Connection first = dataSource.getConnection(); Connection second = dataSource.getConnection()) {
            first.setAutoCommit(false);
            second.setAutoCommit(false);
            first.createStatement().executeUpdate("INSERT INTO top_ups (wallet_id, amount_paise) VALUES (1001, 600000)");
            CompletableFuture<Void> other = CompletableFuture.runAsync(() -> {
                try {
                    second.createStatement().executeUpdate("INSERT INTO top_ups (wallet_id, amount_paise) VALUES (1001, 600000)");   // waits for the wallet lock
                } catch (SQLException e) {
                    throw new IllegalStateException(e);
                }
            });
            Thread.sleep(300);
            assertThat(other).isNotDone();
            first.commit();
            assertThatThrownBy(other::get).hasMessageContaining("top_ups_within_daily_limit");
            second.rollback();
        }
        assertThat(toppedUp(ANANYA)).isEqualTo(600000);
    }

    @Test
    void otherRulesHoldWithoutJava() {
        violates("top_ups_amount_positive", "INSERT INTO top_ups (wallet_id, amount_paise) VALUES (1001, 0)");
        violates("top_ups_wallet_fk", "INSERT INTO top_ups (wallet_id, amount_paise) VALUES (9999, 100)");
        violates("wallets_balance_not_negative", "UPDATE wallets SET balance_paise = -1 WHERE id = 1001");
        violates("wallets_tier_fk", "UPDATE wallets SET tier = 'gold' WHERE id = 1001");
        violates("kyc_tiers_limit_positive", "UPDATE kyc_tiers SET daily_limit_paise = 0 WHERE tier = 'minimum'");
    }

    @Test
    void aTopUpWhoseBalanceCannotBeRaisedLeavesNoRecord() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION refuse_balance() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'balance store down'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_balance BEFORE UPDATE OF balance_paise ON wallets FOR EACH ROW EXECUTE FUNCTION refuse_balance()""").update();
        try {
            assertThatThrownBy(() -> topUp(ANANYA, 100000)).hasRootCauseMessage("ERROR: balance store down\n  Where: PL/pgSQL function refuse_balance() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_balance ON wallets; DROP FUNCTION refuse_balance()").update();
        }
        assertThat(toppedUp(ANANYA)).isZero();
        assertThat(balance(ANANYA)).isEqualTo(50000);
    }
}
