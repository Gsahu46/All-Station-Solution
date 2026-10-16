package com.kartwala.sellerpages;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /seller/products/feed?page&size&sort for the mobile app's endless list: {content, number, size,
 * hasNext}, no totals, so no count query. Same sort rules and the same stable order as the catalog.
 */
class InfiniteScrollChallengeTest extends ApiTest {

    @Test
    void aSliceKnowsOnlyWhetherMoreFollows() throws Exception {
        mvc.perform(get("/seller/products/feed").header("X-Seller-Id", 8).param("size", "20")).andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(20))).andExpect(jsonPath("$.hasNext").value(true)).andExpect(jsonPath("$.totalElements").doesNotExist());
        mvc.perform(get("/seller/products/feed").header("X-Seller-Id", 8).param("size", "20").param("page", "1")).andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(10))).andExpect(jsonPath("$.hasNext").value(false));
        mvc.perform(get("/seller/products/feed").header("X-Seller-Id", 8).param("sort", "sellerId")).andExpect(status().isBadRequest());
    }

    @Test
    void noCountQuery() {
        Counted<Long> counted = counting(() -> {
            try {
                mvc.perform(get("/seller/products/feed").header("X-Seller-Id", 7).param("page", "5")).andExpect(status().isOk());
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            return 0L;
        });
        assertThat(counted.queries()).isEqualTo(2);   // does the seller exist, and the rows
    }
}
