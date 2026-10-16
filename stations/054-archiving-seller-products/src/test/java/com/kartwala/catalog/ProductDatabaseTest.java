package com.kartwala.catalog;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tables' rules with Java bypassed, the JPA callbacks against the real rows, and a rollback. */
class ProductDatabaseTest extends ApiTest {

    @Autowired
    ProductRepository products;
    @Autowired
    TransactionTemplate transaction;

    void insert(long seller, String name, long price, String archivedAt) {
        jdbc.sql("INSERT INTO products (seller_id, name, price_paise, archived_at, created_at, updated_at) VALUES (?, ?, ?, ?::timestamptz, TIMESTAMPTZ '2026-10-01 10:00Z', TIMESTAMPTZ '2026-10-01 10:00Z')")
                .params(seller, name, price, archivedAt).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> insert(1, "Darjeeling tea", 0, null)).hasMessageContaining("products_price_positive");
        assertThatThrownBy(() -> insert(9, "Darjeeling tea", 100, null)).hasMessageContaining("products_seller_fk");
        assertThatThrownBy(() -> insert(1, "Darjeeling tea", 100, "2026-09-30 10:00Z")).hasMessageContaining("products_archived_after_created");
        assertThatThrownBy(() -> jdbc.sql("UPDATE products SET updated_at = created_at - interval '1 second' WHERE id = 1").update())
                .hasMessageContaining("products_updated_after_created");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO order_lines (order_ref, product_id, quantity, unit_price_paise) VALUES ('KW-9', 99, 1, 100)").update())
                .hasMessageContaining("order_lines_product_fk");
    }

    @Test
    void aNameIsUniqueAmongProductsOnSaleOnly() {
        assertThatThrownBy(() -> insert(1, "ASSAM TEA, 500 G", 100, null)).hasMessageContaining("products_seller_name_active");
        insert(2, "Assam tea, 500 g", 100, null);                          // another seller may use the name
        jdbc.sql("UPDATE products SET archived_at = now() WHERE id = 1").update();
        insert(1, "Assam tea, 500 g", 37900, null);                        // once archived, a new one may take it
    }

    @Test
    void prePersistAndPreUpdateStampTheRows() {
        Product saved = products.save(new Product(1, "Darjeeling tea, 250 g", 42900));
        assertThat(saved.getCreatedAt()).isNotNull().isEqualTo(saved.getUpdatedAt());
        assertThat(jdbc.sql("SELECT created_at = updated_at FROM products WHERE id = ?").param(saved.getId()).query(Boolean.class).single()).isTrue();

        transaction.executeWithoutResult(s -> products.findById(saved.getId()).orElseThrow().archive());
        Instant[] stamps = jdbc.sql("SELECT created_at, updated_at FROM products WHERE id = ?").param(saved.getId())
                .query((rs, n) -> new Instant[]{rs.getTimestamp(1).toInstant(), rs.getTimestamp(2).toInstant()}).single();
        assertThat(stamps[1]).isAfter(stamps[0]);
    }

    @Test
    void anArchiveThatFailsLaterIsRolledBack() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(s -> {
            products.findById(1L).orElseThrow().archive();
            products.flush();   // the UPDATE has gone to PostgreSQL...
            throw new IllegalStateException("the search index could not be told");
        })).hasMessageContaining("search index");
        assertThat(jdbc.sql("SELECT archived_at IS NULL FROM products WHERE id = 1").query(Boolean.class).single()).isTrue();   // ...and is undone
    }
}
