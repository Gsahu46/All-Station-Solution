package com.kartwala.wishlist;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: GET /products/most-wished: how many wishlists hold each product, most first. */
class MostWishedChallengeTest extends ApiTest {

    @Test
    void productsAreCountedOncePerWishlistAndRanked() throws Exception {
        add(7, "PH-12");
        add(7, "ph-12");   // same wishlist again: still one
        add(7, "TV-55");
        add(8, "PH-12");
        add(8, "EB-141");
        mvc.perform(get("/products/most-wished").param("limit", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[*].sku", contains("PH-12", "EB-141")))   // ties ordered by SKU
                .andExpect(jsonPath("$[0].wishlists").value(2))
                .andExpect(jsonPath("$[1].wishlists").value(1));
    }

    @Test
    void nothingWishedIsAnEmptyList() throws Exception {
        mvc.perform(get("/products/most-wished")).andExpect(status().isOk()).andExpect(jsonPath("$").isEmpty());
    }
}
