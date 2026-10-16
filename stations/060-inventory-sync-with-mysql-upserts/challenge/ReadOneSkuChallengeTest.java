package com.basketo.inventory;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /warehouses/{id}/stock/{sku} returns {warehouseId, sku, quantity}. The SKU in the path is matched
 * the way the sync stores it, so "rice-5kg" finds RICE-5KG. A SKU the warehouse has never synced is 404.
 */
class ReadOneSkuChallengeTest extends ApiTest {

    @Test
    void aSyncedSkuCanBeReadInAnyCase() throws Exception {
        sync(1, "[{\"sku\":\"RICE-5KG\",\"quantity\":40}]").andExpect(status().isOk());
        mvc.perform(get("/warehouses/1/stock/rice-5kg")).andExpect(status().isOk())
                .andExpect(jsonPath("$.warehouseId").value(1)).andExpect(jsonPath("$.sku").value("RICE-5KG")).andExpect(jsonPath("$.quantity").value(40));
    }

    @Test
    void aSkuOfAnotherWarehouseOrNoneIs404() throws Exception {
        sync(1, "[{\"sku\":\"RICE-5KG\",\"quantity\":40}]").andExpect(status().isOk());
        mvc.perform(get("/warehouses/2/stock/RICE-5KG")).andExpect(status().isNotFound());
        mvc.perform(get("/warehouses/1/stock/OIL-1L")).andExpect(status().isNotFound());
    }
}
