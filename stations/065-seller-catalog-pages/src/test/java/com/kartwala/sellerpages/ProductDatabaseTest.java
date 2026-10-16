package com.kartwala.sellerpages;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules as PostgreSQL enforces them, with plain SQL; test products belong to seller 8 and start with "Test". */
class ProductDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    @AfterEach
    void removeTestProducts() {
        jdbc.sql("DELETE FROM products WHERE name LIKE 'Test%'").update();
    }

    private void product(long seller, String name, int paise) {
        jdbc.sql("INSERT INTO products (seller_id, name, price_paise, created_on) VALUES (?, ?, ?, DATE '2026-10-01')").params(seller, name, paise).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        product(8, "Test Dupatta", 50000);
        assertThatThrownBy(() -> product(8, "Test Dupatta", 60000)).isInstanceOf(DataAccessException.class).hasMessageContaining("products_name_per_seller");
        product(7, "Test Dupatta", 60000);   // another seller may use the same name
        assertThatThrownBy(() -> product(8, "Test Free", 0)).hasMessageContaining("products_price_range");
        assertThatThrownBy(() -> product(8, "  ", 50000)).hasMessageContaining("products_name_not_blank");
        assertThatThrownBy(() -> product(99, "Test Orphan", 50000)).hasMessageContaining("products_seller_fk");
    }

    @Test
    void anUploadWithOneBadPriceAddsNothing() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> {
            product(8, "Test Shawl", 120000);
            product(8, "Test Stole", 90000);
            product(8, "Test Typo", 99_999_999);
        })).hasMessageContaining("products_price_range");
        assertThat(jdbc.sql("SELECT count(*) FROM products WHERE name LIKE 'Test%'").query(Long.class).single()).isZero();
    }
}
