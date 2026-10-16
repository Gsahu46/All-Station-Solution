package com.kartwala.checkout;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tables' rules with Java bypassed, and Spring's rollback rules and read-only mode against the real database. */
@Import(RollbackRules.class)
class CheckoutDatabaseTest extends ApiTest {

    @Autowired
    RollbackRules rules;

    long orders() {
        return jdbc.sql("SELECT count(*) FROM orders").query(Long.class).single();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> jdbc.sql("UPDATE products SET stock = -1 WHERE id = 2").update()).hasMessageContaining("products_stock_not_negative");
        long order = jdbc.sql("INSERT INTO orders (customer_id, total_paise) VALUES (7, 100) RETURNING id").query(Long.class).single();
        jdbc.sql("INSERT INTO payments (order_id, amount_paise, status) VALUES (?, 100, 'CAPTURED')").param(order).update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO payments (order_id, amount_paise, status) VALUES (?, 100, 'CAPTURED')").param(order).update())
                .hasMessageContaining("payments_one_per_order");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO payments (order_id, amount_paise, status) VALUES (99, 100, 'CAPTURED')").update())
                .hasMessageContaining("payments_order_fk");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO reservations (order_id, product_id, quantity, unit_price_paise) VALUES (?, 1, 0, 100)").param(order).update())
                .hasMessageContaining("reservations_quantity_range");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO orders (customer_id, total_paise, status) VALUES (7, 100, 'LOST')").update())
                .hasMessageContaining("orders_status_known");
    }

    @Test
    void aCheckedExceptionCommitsUnlessToldOtherwise() {
        assertThatThrownBy(rules::checkedException).isInstanceOf(RollbackRules.PaymentDeclined.class);
        assertThat(orders()).isEqualTo(1);   // the order survived its own failure
        assertThatThrownBy(rules::checkedExceptionWithRollbackFor).isInstanceOf(RollbackRules.PaymentDeclined.class);
        assertThat(orders()).isEqualTo(1);   // rollbackFor: this one did not
        assertThatThrownBy(rules::uncheckedException).isInstanceOf(IllegalStateException.class);
        assertThat(orders()).isEqualTo(1);
    }

    @Test
    void aReadOnlyTransactionRefusesWrites() {
        assertThatThrownBy(rules::writeInReadOnly).hasMessageContaining("read-only transaction");
        assertThat(orders()).isZero();
    }
}
