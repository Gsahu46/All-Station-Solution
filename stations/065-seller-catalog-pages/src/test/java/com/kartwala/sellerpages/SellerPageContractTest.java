package com.kartwala.sellerpages;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class SellerPageContractTest extends ApiTest {

    @Test
    void theFirstPageByName() throws Exception {
        mvc.perform(get("/seller/products").header("X-Seller-Id", 7)).andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(20))).andExpect(jsonPath("$.content[0].name").value("Product 0001"))
                .andExpect(jsonPath("$.page.number").value(0)).andExpect(jsonPath("$.page.size").value(20))
                .andExpect(jsonPath("$.page.totalElements").value(2000)).andExpect(jsonPath("$.page.totalPages").value(100));
    }

    @Test
    void sortedByPriceDearestFirstTiesByIdOnPageTwo() throws Exception {
        // 200 products cost Rs 190; page 1 of size 50 holds the 51st to 100th of them, in id order.
        mvc.perform(get("/seller/products").header("X-Seller-Id", 7).param("sort", "pricePaise,desc").param("size", "50").param("page", "1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content[0].pricePaise").value(19000)).andExpect(jsonPath("$.content[0].id").value(507))
                .andExpect(jsonPath("$.content[49].id").value(997));
    }

    @Test
    void aSizeAbove100IsCutTo100AndTheResponseSaysSo() throws Exception {
        mvc.perform(get("/seller/products").header("X-Seller-Id", 7).param("size", "5000")).andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(100))).andExpect(jsonPath("$.page.size").value(100)).andExpect(jsonPath("$.page.totalPages").value(20));
    }

    @Test
    void aPagePastTheEndIsEmptyAndAnotherSellersProductsNeverShow() throws Exception {
        mvc.perform(get("/seller/products").header("X-Seller-Id", 7).param("page", "100")).andExpect(status().isOk())
                .andExpect(jsonPath("$.content", empty())).andExpect(jsonPath("$.page.totalElements").value(2000));
        mvc.perform(get("/seller/products").header("X-Seller-Id", 8).param("size", "100")).andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(30))).andExpect(jsonPath("$.content[0].name").value("Saree 01"));
    }

    @Test
    void anUnknownSellerIs404() throws Exception {
        mvc.perform(get("/seller/products").header("X-Seller-Id", 99)).andExpect(status().isNotFound());
    }

    @Test
    void aSortOutsideTheListOrNoSellerIs400() throws Exception {
        mvc.perform(get("/seller/products").header("X-Seller-Id", 7).param("sort", "sellerId")).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("Sort by one of [createdOn, name, pricePaise]"));
        mvc.perform(get("/seller/products").header("X-Seller-Id", 7).param("sort", "name; DROP TABLE products")).andExpect(status().isBadRequest());
        mvc.perform(get("/seller/products")).andExpect(status().isBadRequest());
        mvc.perform(get("/seller/products").header("X-Seller-Id", "seven")).andExpect(status().isBadRequest());
    }
}
