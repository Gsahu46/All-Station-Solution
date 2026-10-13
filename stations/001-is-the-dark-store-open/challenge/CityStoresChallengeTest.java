package com.basketo.stores;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: GET /stores?city=BLR lists every store in a city, open or closed, sorted by id. */
class CityStoresChallengeTest extends ApiTest {

    @Test
    void listsEveryStoreInTheCitySortedById() throws Exception {
        mvc.perform(get("/stores").param("city", "BLR"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(3)))
                .andExpect(jsonPath("$[0].storeId").value("BLR-HSR-02"))
                .andExpect(jsonPath("$[1].storeId").value("BLR-IND-01"))
                .andExpect(jsonPath("$[1].open").value(false))
                .andExpect(jsonPath("$[2].storeId").value("BLR-KOR-01"));
    }

    @Test
    void aCityWithNoStoresIsAnEmptyListNotA404() throws Exception {
        // A collection always exists; it can be empty. 404 is for one resource that does not exist.
        mvc.perform(get("/stores").param("city", "PNQ"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(0)));
    }

    @Test
    void missingCityIs400() throws Exception {
        mvc.perform(get("/stores")).andExpect(status().isBadRequest());
    }
}
