package com.kartwala.catalog;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.notNullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: archive and list; valid, invalid and not found. */
class SellerProductContractTest extends ApiTest {

    @Test
    void anArchivedProductLeavesTheDefaultList() throws Exception {
        list(1, null).andExpect(jsonPath("$[*].id", contains(1, 2)));
        archive(1, 1).andExpect(status().isNoContent());
        list(1, null).andExpect(jsonPath("$[*].id", contains(2)));
        list(1, "true").andExpect(jsonPath("$[*].id", contains(1, 2)))
                .andExpect(jsonPath("$[0].archived").value(true)).andExpect(jsonPath("$[0].archivedAt", notNullValue()))
                .andExpect(jsonPath("$[1].archived").value(false)).andExpect(jsonPath("$[1].archivedAt").doesNotExist());
    }

    @Test
    void archivingStampsUpdatedAtAndAgainChangesNothing() throws Exception {
        archive(1, 1);
        String first = jdbc.sql("SELECT archived_at || ' ' || updated_at FROM products WHERE id = 1").query(String.class).single();
        archive(1, 1).andExpect(status().isNoContent());   // DELETE is idempotent: the same answer, nothing new
        org.assertj.core.api.Assertions.assertThat(jdbc.sql("SELECT archived_at || ' ' || updated_at FROM products WHERE id = 1").query(String.class).single())
                .isEqualTo(first);
        list(1, "true").andExpect(jsonPath("$[0].createdAt").value("2026-09-01T04:30:00Z"))
                .andExpect(jsonPath("$[0].updatedAt").value(org.hamcrest.Matchers.not("2026-09-01T04:30:00Z")));
    }

    @Test
    void anotherSellersProductIsNotFound() throws Exception {
        archive(2, 1).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No product 1 in your catalogue."));
        archive(1, 999).andExpect(status().isNotFound());
        list(2, null).andExpect(jsonPath("$[*].id", contains(3)));
    }

    @Test
    void requestsWithoutASellerOrWithBadParametersAre400() throws Exception {
        mvc.perform(delete("/seller/products/1")).andExpect(status().isBadRequest());
        mvc.perform(get("/seller/products").header("X-Seller-Id", "chaiwala")).andExpect(status().isBadRequest());
        list(1, "maybe").andExpect(status().isBadRequest());
        mvc.perform(delete("/seller/products/tea").header("X-Seller-Id", 1)).andExpect(status().isBadRequest());
    }
}
