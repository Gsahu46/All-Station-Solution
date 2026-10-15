package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The table's rules with Java bypassed, and what a rollback does to the sequence. */
class OrderDatabaseTest extends ApiTest {

    void insert(String number, long paise) {
        jdbc.sql("INSERT INTO orders (order_number, outlet_id, total_paise) VALUES (?, 'TF-07', ?)").params(number, paise).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        insert("TF-1000001-8", 100);
        assertThatThrownBy(() -> insert("TF-1000001-8", 100)).hasMessageContaining("orders_number_unique");
        assertThatThrownBy(() -> insert("#42", 100)).hasMessageContaining("orders_number_format");
        assertThatThrownBy(() -> insert("TF-1000002-6", 0)).hasMessageContaining("orders_total_positive");
    }

    @Test
    void aRolledBackOrderLeavesAGapNotARepeat() {
        String first = store.place("TF-07", 45_000).orderNumber();
        assertThatThrownBy(() -> store.place("TF-07", 0)).hasMessageContaining("orders_total_positive");   // Java checks bypassed
        String third = store.place("TF-07", 45_000).orderNumber();
        assertThat(orders()).isEqualTo(2);
        long a = Long.parseLong(first.substring(3, 10));
        long c = Long.parseLong(third.substring(3, 10));
        assertThat(c).isEqualTo(a + 2);   // the failed order used a number, and nobody will ever get it
    }

    @Test
    void theSequenceRefusesToWrapAround() {
        assertThat(jdbc.sql("SELECT seqmax, seqcycle FROM pg_sequence WHERE seqrelid = 'order_number_seq'::regclass")
                .query((rs, n) -> rs.getLong(1) + " " + rs.getBoolean(2)).single()).isEqualTo("9999999 false");
    }
}
