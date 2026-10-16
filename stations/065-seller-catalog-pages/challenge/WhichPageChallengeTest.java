package com.kartwala.sellerpages;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /seller/products/{id}/page?size&sort=pricePaise (or pricePaise,desc) answers {productId, page}:
 * the page that product is on in the catalog's stable order, so "edit, then back to the list" returns to the right
 * page. Count the rows before it in SQL, never by reading the pages. Another seller's product is 404.
 */
class WhichPageChallengeTest extends ApiTest {

    @Test
    void thePageAProductIsOn() throws Exception {
        // Product 1 costs Rs 170: 1,400 products are cheaper, none of them cost the same with a smaller id.
        mvc.perform(get("/seller/products/1/page").header("X-Seller-Id", 7).param("size", "20").param("sort", "pricePaise")).andExpect(status().isOk())
                .andExpect(jsonPath("$.productId").value(1)).andExpect(jsonPath("$.page").value(70));
        mvc.perform(get("/seller/products/1/page").header("X-Seller-Id", 7).param("size", "20").param("sort", "pricePaise,desc")).andExpect(status().isOk())
                .andExpect(jsonPath("$.page").value(20));
        mvc.perform(get("/seller/products/507/page").header("X-Seller-Id", 7).param("size", "50").param("sort", "pricePaise,desc")).andExpect(status().isOk())
                .andExpect(jsonPath("$.page").value(1));
    }

    @Test
    void anotherSellersProductIs404() throws Exception {
        mvc.perform(get("/seller/products/2001/page").header("X-Seller-Id", 7).param("sort", "pricePaise")).andExpect(status().isNotFound());
    }
}
