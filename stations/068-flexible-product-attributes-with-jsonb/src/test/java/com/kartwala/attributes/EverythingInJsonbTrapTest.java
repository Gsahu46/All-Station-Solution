package com.kartwala.attributes;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Written first. The old table kept the whole product in one jsonb column, price and seller included, on a copy of
 * the demo catalog. Then the same mistakes against the real table.
 */
class EverythingInJsonbTrapTest extends ApiTest {

    @BeforeEach
    void oldTable() {
        jdbc.sql("CREATE TABLE old_products (id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, data JSONB NOT NULL)").update();
        jdbc.sql("""
                INSERT INTO old_products (data) SELECT jsonb_build_object('sku', sku, 'name', name, 'category', category_code,
                    'seller', seller_id, 'price', price_paise) || attributes FROM products""").update();
    }

    @AfterEach
    void dropOldTable() {
        jdbc.sql("DROP TABLE old_products").update();
    }

    @Test
    void anythingGetsIntoTheOldTable() {
        jdbc.sql("INSERT INTO old_products (data) VALUES ('{\"sku\": \"PH-NOVA-8-128\", \"price\": \"free\", \"seller\": 999, \"ram\": \"lots\"}')").update();
        assertThat(jdbc.sql("SELECT count(*) FROM old_products WHERE data->>'sku' = 'PH-NOVA-8-128'").query(Long.class).single()).isEqualTo(2);   // a duplicate SKU
    }

    @Test
    void oneBadPriceBreaksEveryPriceQuery() {
        String under2000 = "SELECT count(*) FROM old_products WHERE (data->>'price')::int < 200000";
        assertThat(jdbc.sql(under2000).query(Long.class).single()).isPositive();
        jdbc.sql("INSERT INTO old_products (data) VALUES ('{\"sku\": \"T-ODD\", \"price\": \"free\"}')").update();
        assertThatThrownBy(() -> jdbc.sql(under2000).query(Long.class).single()).rootCause()
                .hasMessageContaining("invalid input syntax for type integer: \"free\"");   // every customer's price filter now fails
    }

    @Test
    void theRealTableRefusesTheSameRows() {
        String insert = "INSERT INTO products (sku, name, category_code, seller_id, price_paise, attributes) VALUES (?, 'X', 'phones', ?, ?, '{}')";
        assertThatThrownBy(() -> jdbc.sql(insert).params("PH-NOVA-8-128", 7, 100000).update()).isInstanceOf(DataAccessException.class).hasMessageContaining("products_sku_unique");
        assertThatThrownBy(() -> jdbc.sql(insert).params("T-FREE", 7, 0).update()).hasMessageContaining("products_price_range");
        assertThatThrownBy(() -> jdbc.sql(insert).params("T-NOBODY", 999, 100000).update()).hasMessageContaining("products_seller_fk");
    }

    @Test
    void containmentUsesTheGinIndexTheArrowOperatorDoesNot() {
        assertThat(indexesUsed("SELECT id FROM products WHERE attributes @> CAST(:wanted AS jsonb)", Map.of("wanted", "{\"ram\": \"12GB\"}")))
                .containsExactly("products_attributes");
        assertThat(indexesUsed("SELECT id FROM products WHERE attributes->>'ram' = :ram", Map.of("ram", "12GB"))).isEmpty();
    }
}
