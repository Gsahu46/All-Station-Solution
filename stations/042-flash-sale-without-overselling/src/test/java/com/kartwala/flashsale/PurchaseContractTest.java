package com.kartwala.flashsale;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract against the demo sales. */
class PurchaseContractTest extends ApiTest {

    @Test
    void aBuyerGetsOnePhoneAtTheSalePrice() throws Exception {
        buy(1, "c-000123").andExpect(status().isCreated())
                .andExpect(jsonPath("$.saleId").value(1))
                .andExpect(jsonPath("$.customerId").value("C-000123"))
                .andExpect(jsonPath("$.pricePaise").value(999900));
        buy(1, "C-000123").andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Already bought"));
    }

    @Test
    void eachRefusalSaysWhy() throws Exception {
        buy(2, "C-000123").andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Sold out"));
        buy(3, "C-000123").andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Sale ended"));
        buy(4, "C-000123").andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Not started"));
        buy(99, "C-000123").andExpect(status().isNotFound()).andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
    }

    @Test
    void badRequestsAre400() throws Exception {
        buy(1, "123").andExpect(status().isBadRequest());
        mvc.perform(post("/flash-sales/1/purchases").contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isBadRequest());
        mvc.perform(post("/flash-sales/1/purchases").contentType(MediaType.APPLICATION_JSON)
                .content("{\"customerId\":\"C-000123\",\"quantity\":5}")).andExpect(status().isBadRequest());
        mvc.perform(post("/flash-sales/abc/purchases").contentType(MediaType.APPLICATION_JSON)
                .content("{\"customerId\":\"C-000123\"}")).andExpect(status().isBadRequest());
    }
}
