package com.kartwala.catalog;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /catalog/products/{id} returns one product by the id in its Location header. An id that is not
 * 24 hex digits is 400; a well-formed id nobody has is 404.
 */
class ProductByIdChallengeTest extends ApiTest {

    @Test
    void theLocationHeaderLeadsToTheProduct() throws Exception {
        String location = create(CatalogContractTest.SAREE).andReturn().getResponse().getHeader("Location");
        mvc.perform(get(location)).andExpect(status().isOk()).andExpect(jsonPath("$.sku").value("T-SAREE-SILK-RED"));
    }

    @Test
    void malformedIs400AndUnknownIs404() throws Exception {
        mvc.perform(get("/catalog/products/not-an-id")).andExpect(status().isBadRequest());
        mvc.perform(get("/catalog/products/000000000000000000000000")).andExpect(status().isNotFound());
    }
}
