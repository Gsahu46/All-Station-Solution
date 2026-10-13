package com.basketo.stores;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: what the app can rely on for every kind of store id. */
class StoreStatusContractTest extends ApiTest {

    @Test
    void openStoreIs200WithADeliveryPromise() throws Exception {
        mvc.perform(get("/stores/BLR-KOR-01/status"))
                .andExpect(status().isOk())
                .andExpect(content().contentType("application/json"))
                .andExpect(jsonPath("$.storeId").value("BLR-KOR-01"))
                .andExpect(jsonPath("$.name").value("Koramangala"))
                .andExpect(jsonPath("$.open").value(true))
                .andExpect(jsonPath("$.reason").isEmpty())
                .andExpect(jsonPath("$.deliveryPromiseMinutes").value(10));
    }

    @Test
    void closedStoreIs200WithAReasonAndNoDeliveryPromise() throws Exception {
        mvc.perform(get("/stores/BLR-IND-01/status"))
                .andExpect(status().isOk())                 // the store exists; "closed" is its state, not an error
                .andExpect(jsonPath("$.open").value(false))
                .andExpect(jsonPath("$.reason").value("Closed for stock-taking"))
                .andExpect(jsonPath("$.deliveryPromiseMinutes").isEmpty());
    }

    @Test
    void unknownStoreIs404Problem() throws Exception {
        mvc.perform(get("/stores/BLR-XYZ-99/status"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType("application/problem+json"))
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.title").value("Store not found"))
                .andExpect(jsonPath("$.detail").value("No dark store has the id BLR-XYZ-99."))
                .andExpect(jsonPath("$.instance").value("/stores/BLR-XYZ-99/status"));
    }

    @Test
    void malformedStoreIdIs400Problem() throws Exception {
        mvc.perform(get("/stores/koramangala/status"))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType("application/problem+json"))
                .andExpect(jsonPath("$.title").value("Invalid store id"));
    }

    @Test
    void anotherPathUnderStoresIs404() throws Exception {
        mvc.perform(get("/stores/BLR-KOR-01")).andExpect(status().isNotFound());
        mvc.perform(get("/stores/BLR-KOR-01/status/")).andExpect(status().isNotFound()); // no trailing-slash matching
    }

    @Test
    void postIsNotAllowedOnTheStatus() throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post("/stores/BLR-KOR-01/status"))
                .andExpect(status().isMethodNotAllowed());
    }
}
