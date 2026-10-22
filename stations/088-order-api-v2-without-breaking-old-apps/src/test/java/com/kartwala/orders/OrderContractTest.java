package com.kartwala.orders;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class OrderContractTest {

    @Autowired
    MockMvc mvc;

    @Test
    void v1KeepsTheShapeOldAppsParse() throws Exception {
        mvc.perform(get("/v1/orders/1001")).andExpect(status().isOk()).andExpect(content().json("""
                {"id":1001,"customerName":"Meera Iyer","total":1299.50,"status":"SHIPPED",
                 "items":[{"sku":"KW-TEE-01","qty":2,"price":499.75},{"sku":"KW-CAP-07","qty":1,"price":300.00}],
                 "trackingUrl":"https://track.example/KW1001"}""", true));
    }

    @Test
    void v2HasTheNewShape() throws Exception {
        mvc.perform(get("/v2/orders/1001")).andExpect(status().isOk()).andExpect(content().json("""
                {"id":1001,"customer":{"name":"Meera Iyer","phone":"+919800000001"},
                 "items":[{"sku":"KW-TEE-01","quantity":2,"unitPricePaise":49975},{"sku":"KW-CAP-07","quantity":1,"unitPricePaise":30000}],
                 "totalPaise":129950,"currency":"INR","status":"shipped","placedAt":"2026-10-20T09:15:00Z","trackingUrl":"https://track.example/KW1001"}""", true));
        mvc.perform(get("/v2/orders/1002")).andExpect(jsonPath("$.trackingUrl").isEmpty()).andExpect(jsonPath("$.status").value("placed"));
    }

    @Test
    void v1IsMarkedDeprecatedWithItsEndDateAndV2IsNot() throws Exception {
        mvc.perform(get("/v1/orders/1001"))
                .andExpect(header().string("Deprecation", "@1790793000"))                    // 1 Oct 2026, 00:00 IST
                .andExpect(header().string("Sunset", "Wed, 31 Mar 2027 18:30:00 GMT"))         // 1 Apr 2027, 00:00 IST
                .andExpect(header().string("Link", "<https://developer.kartwala.example/orders/v1-to-v2>; rel=\"deprecation\"; type=\"text/html\""));
        mvc.perform(get("/v2/orders/1001")).andExpect(header().doesNotExist("Deprecation")).andExpect(header().doesNotExist("Sunset"));
    }

    @Test
    void unknownOrdersAre404AndBadIdsOrVersionsAre400() throws Exception {
        mvc.perform(get("/v1/orders/9")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such order"));
        mvc.perform(get("/v2/orders/9")).andExpect(status().isNotFound());
        mvc.perform(get("/v2/orders/abc")).andExpect(status().isBadRequest());
        mvc.perform(get("/v3/orders/1001")).andExpect(status().isBadRequest()).andExpect(jsonPath("$.detail").value("Invalid API version: '3.0.0'."));
        mvc.perform(get("/v2/orders/1001/")).andExpect(status().isNotFound());   // no trailing-slash matching
    }
}
