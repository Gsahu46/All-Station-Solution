package com.kartwala.attributes;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules as PostgreSQL enforces them, with plain SQL; test rows use SKUs starting with T-. */
class ProductDatabaseTest extends ApiTest {

    private void product(String sku, String category, long seller, int paise, String attributes) {
        jdbc.sql("INSERT INTO products (sku, name, category_code, seller_id, price_paise, attributes) VALUES (?, 'Test', ?, ?, ?, CAST(? AS jsonb))")
                .params(sku, category, seller, paise, attributes).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> product("T-ARRAY", "phones", 7, 100000, "[\"8GB\"]")).isInstanceOf(DataAccessException.class).hasMessageContaining("products_attributes_object");
        assertThatThrownBy(() -> product("T-LAPTOP", "laptops", 7, 100000, "{}")).hasMessageContaining("products_category_fk");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO attribute_definitions (category_code, name, required) VALUES ('phones', 'Battery Life', false)").update())
                .hasMessageContaining("attribute_definitions_name_shape");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO attribute_definitions (category_code, name, required) VALUES ('phones', 'ram', false)").update())
                .hasMessageContaining("attribute_definitions_pk");
    }

    @Test
    void anUploadWithOneBadRowAddsNothing() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> {
            product("T-ONE", "shoes", 8, 99900, "{\"size\": \"8\", \"colour\": \"Red\"}");
            product("T-TWO", "shoes", 8, 99900, "{\"size\": \"9\", \"colour\": \"Red\"}");
            product("T-THREE", "shoes", 9, 99900, "{\"size\": \"10\", \"colour\": \"Red\"}");
        })).hasMessageContaining("products_seller_fk");
        assertThat(jdbc.sql("SELECT count(*) FROM products WHERE sku LIKE 'T-%'").query(Long.class).single()).isZero();
    }

    @Test
    void jsonbStoresTheDocumentNormalised() {
        product("T-ORDER", "shoes", 8, 99900, "{\"size\": \"8\", \"colour\": \"Red\", \"colour\": \"Blue\"}");
        // Keys sorted by length then bytes, whitespace dropped, and the last duplicate key wins: jsonb is not the text you sent.
        assertThat(jdbc.sql("SELECT attributes::text FROM products WHERE sku = 'T-ORDER'").query(String.class).single())
                .isEqualTo("{\"size\": \"8\", \"colour\": \"Blue\"}");
    }
}
