package com.tiffino.ordering;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tables' rules with Java bypassed, and an order saved with its lines or not at all. */
class OrderDatabaseTest extends ApiTest {

    @Autowired
    OrderService service;

    long insertOrder(String phone, String pincode, String status, long total) {
        return jdbc.sql("INSERT INTO orders (customer_name, phone, address_line, city, pincode, status, total_paise) VALUES ('T', ?, 'x', 'Pune', ?, ?, ?) RETURNING id")
                .params(phone, pincode, status, total).query(Long.class).single();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> insertOrder("12345", "411045", "PLACED", 100)).hasMessageContaining("orders_phone_digits");
        assertThatThrownBy(() -> insertOrder("9876543210", "011045", "PLACED", 100)).hasMessageContaining("orders_pincode_digits");
        assertThatThrownBy(() -> insertOrder("9876543210", "411045", "LOST", 100)).hasMessageContaining("orders_status_known");
        assertThatThrownBy(() -> insertOrder("9876543210", "411045", "PLACED", 0)).hasMessageContaining("orders_total_positive");
        long id = insertOrder("9876543210", "411045", "PLACED", 100);
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO order_lines (order_id, item, quantity, unit_price_paise) VALUES (?, 'x', 0, 100)").param(id).update())
                .hasMessageContaining("order_lines_quantity_range");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO order_lines (order_id, item, quantity, unit_price_paise) VALUES (999, 'x', 1, 100)").update())
                .hasMessageContaining("order_lines_order_fk");
    }

    @Test
    void aBadLineRollsBackTheWholeOrder() {
        // Validation bypassed: the service is called directly with a quantity the database refuses.
        OrderDtos.CreateOrderRequest bad = request(ORDER.replace("\"quantity\":1", "\"quantity\":50"));
        assertThatThrownBy(() -> service.place(bad)).hasMessageContaining("order_lines_quantity_range");
        assertThat(jdbc.sql("SELECT count(*) FROM orders").query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT count(*) FROM order_lines").query(Long.class).single()).isZero();
    }
}
