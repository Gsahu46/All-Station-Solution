package com.basketo.loyalty;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tables' rules with Java bypassed, a rollback of both rows, and the upsert under concurrency. */
class LoyaltyDatabaseTest extends ApiTest {

    @Autowired
    LoyaltyLedger ledger;
    @Autowired
    TransactionTemplate transaction;

    @Test
    void namedConstraintsHoldWithoutJava() {
        long c = newCustomer();
        jdbc.sql("INSERT INTO point_balances (customer_id, points) VALUES (?, 5)").param(c).update();
        assertThatThrownBy(() -> jdbc.sql("UPDATE point_balances SET points = -1 WHERE customer_id = ?").param(c).update()).hasMessageContaining("point_balances_not_negative");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO point_balances (customer_id, points) VALUES (999999, 1)").update()).hasMessageContaining("point_balances_customer_fk");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO point_entries (customer_id, delta, reason) VALUES (?, 5, 'EARN')").param(c).update()).hasMessageContaining("point_entries_sign_matches");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO point_entries (customer_id, delta, reason) VALUES (?, 5, 'REDEEM')").param(c).update()).hasMessageContaining("point_entries_sign_matches");
        jdbc.sql("INSERT INTO point_entries (customer_id, order_ref, delta, reason) VALUES (?, 'BK-1', 5, 'EARN')").param(c).update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO point_entries (customer_id, order_ref, delta, reason) VALUES (?, 'BK-1', 5, 'EARN')").param(c).update())
                .hasMessageContaining("point_entries_order_once");
    }

    @Test
    void anEarnThatFailsAfterItsWritesLeavesNeither() {
        long c = newCustomer();
        assertThatThrownBy(() -> transaction.executeWithoutResult(s -> {
            ledger.earn(c, "BK-6001", 500_000);   // joins this transaction: entry and balance written...
            throw new IllegalStateException("the order system called back: payment failed");
        })).hasMessageContaining("payment failed");
        assertThat(balance(c)).isNull();   // ...and both rolled back
        assertThat(jdbc.sql("SELECT count(*) FROM point_entries WHERE customer_id = ?").param(c).query(Long.class).single()).isZero();
    }

    @Test
    void twentyEarnsAtOnceForANewCustomerAddUp() throws Exception {
        long c = newCustomer();   // no balance row yet: twenty requests race to create it
        AtomicInteger order = new AtomicInteger();
        List<Integer> statuses = together(20, () -> earn(c, "BK-7" + order.incrementAndGet(), 100_000).andReturn().getResponse().getStatus());
        assertThat(statuses).containsOnly(201);
        assertThat(balance(c)).isEqualTo(200);   // 20 orders x 10 points: the upsert never lost one
    }
}
