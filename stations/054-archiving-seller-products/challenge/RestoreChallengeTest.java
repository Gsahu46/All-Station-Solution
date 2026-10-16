package com.kartwala.catalog;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /seller/products/{id}/restore puts an archived product back on sale (archivedAt cleared,
 * updatedAt moved). If the seller has since listed another product with the same name, the database refuses: 409.
 */
class RestoreChallengeTest extends ApiTest {

    @Test
    void anArchivedProductComesBack() throws Exception {
        archive(1, 1);
        mvc.perform(post("/seller/products/1/restore").header("X-Seller-Id", 1)).andExpect(status().isOk())
                .andExpect(jsonPath("$.archived").value(false)).andExpect(jsonPath("$.archivedAt").doesNotExist());
        list(1, null).andExpect(jsonPath("$.length()").value(2));
        mvc.perform(post("/seller/products/1/restore").header("X-Seller-Id", 2)).andExpect(status().isNotFound());
    }

    @Test
    void notOverAnotherProductWithTheSameName() throws Exception {
        archive(1, 1);
        jdbc.sql("INSERT INTO products (seller_id, name, price_paise, created_at, updated_at) VALUES (1, 'Assam Tea, 500 g', 37900, now(), now())").update();
        mvc.perform(post("/seller/products/1/restore").header("X-Seller-Id", 1)).andExpect(status().isConflict());
    }
}
