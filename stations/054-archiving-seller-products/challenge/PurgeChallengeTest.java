package com.kartwala.catalog;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: DELETE /seller/products/{id}?purge=true really deletes an archived product that no order ever had:
 * 204, and it is gone even with includeArchived. A product still on sale, or one that orders point at, is 409; let
 * the database's RESTRICT decide the second, not a count in Java.
 */
class PurgeChallengeTest extends ApiTest {

    @Test
    void onlyArchivedProductsNoOrderHadCanBePurged() throws Exception {
        jdbc.sql("INSERT INTO products (id, seller_id, name, price_paise, archived_at, created_at, updated_at) VALUES (40, 1, 'Typo prodcut', 100, now(), now(), now())").update();
        mvc.perform(delete("/seller/products/40").param("purge", "true").header("X-Seller-Id", 1)).andExpect(status().isNoContent());
        assertThat(jdbc.sql("SELECT count(*) FROM products WHERE id = 40").query(Long.class).single()).isZero();

        mvc.perform(delete("/seller/products/2").param("purge", "true").header("X-Seller-Id", 1)).andExpect(status().isConflict());   // still on sale
        archive(1, 1);
        mvc.perform(delete("/seller/products/1").param("purge", "true").header("X-Seller-Id", 1)).andExpect(status().isConflict());   // in KW-1001
        assertThat(linesOfOrder("KW-1001")).isEqualTo(2);
        mvc.perform(delete("/seller/products/999").param("purge", "true").header("X-Seller-Id", 1)).andExpect(status().isNotFound());
    }
}
