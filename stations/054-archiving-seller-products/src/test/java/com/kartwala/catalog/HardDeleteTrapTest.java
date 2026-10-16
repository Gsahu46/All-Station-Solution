package com.kartwala.catalog;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: the old schema and the old DELETE, then the same request today. The old
 * tables are created inside a transaction that is rolled back, so they never outlive the test.
 */
class HardDeleteTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    @Test
    void theOldCascadeDeletedTheOrderHistoryWithTheProduct() {
        List<Long> before = new java.util.ArrayList<>(), after = new java.util.ArrayList<>();
        transaction.executeWithoutResult(status -> {
            jdbc.sql("CREATE TABLE old_products (id BIGINT PRIMARY KEY, name TEXT)").update();
            // ON DELETE CASCADE "so deleting a product does not fail": it deletes the lines that sold it.
            jdbc.sql("CREATE TABLE old_order_lines (order_ref TEXT, product_id BIGINT REFERENCES old_products ON DELETE CASCADE, quantity INT, unit_price_paise BIGINT)").update();
            jdbc.sql("INSERT INTO old_products VALUES (1, 'Assam tea, 500 g'), (2, 'Masala chai mix, 200 g')").update();
            jdbc.sql("INSERT INTO old_order_lines VALUES ('KW-1001', 1, 2, 34900), ('KW-1001', 2, 1, 19900)").update();
            before.add(jdbc.sql("SELECT sum(quantity * unit_price_paise) FROM old_order_lines WHERE order_ref = 'KW-1001'").query(Long.class).single());
            jdbc.sql("DELETE FROM old_products WHERE id = 1").update();   // the seller "deletes" Assam tea
            after.add(jdbc.sql("SELECT sum(quantity * unit_price_paise) FROM old_order_lines WHERE order_ref = 'KW-1001'").query(Long.class).single());
            status.setRollbackOnly();
        });
        assertThat(before).containsExactly(89700L);   // ₹897 paid by the customer
        assertThat(after).containsExactly(19900L);    // and now the order says ₹199: a line of a paid order is gone
    }

    @Test
    void todayTheDatabaseRefusesTheHardDelete() {
        assertThatThrownBy(() -> jdbc.sql("DELETE FROM products WHERE id = 1").update()).hasMessageContaining("order_lines_product_fk");
        assertThat(linesOfOrder("KW-1001")).isEqualTo(2);
    }

    @Test
    void andTheApiArchivesInstead() throws Exception {
        archive(1, 1).andExpect(status().isNoContent());
        assertThat(linesOfOrder("KW-1001")).isEqualTo(2);
        assertThat(jdbc.sql("SELECT p.name FROM order_lines l JOIN products p ON p.id = l.product_id WHERE l.order_ref = 'KW-1001' ORDER BY l.id")
                .query(String.class).list()).containsExactly("Assam tea, 500 g", "Masala chai mix, 200 g");   // the history still reads
    }
}
