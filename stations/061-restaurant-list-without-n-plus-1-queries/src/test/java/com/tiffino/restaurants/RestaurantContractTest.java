package com.tiffino.restaurants;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RestaurantContractTest extends ApiTest {

    @Test
    void mumbaiListsItsRestaurantsWithCuisinesAndRatings() throws Exception {
        mvc.perform(get("/restaurants").param("city", "mumbai")).andExpect(status().isOk())
                .andExpect(jsonPath("$.city").value("mumbai")).andExpect(jsonPath("$.page").value(0)).andExpect(jsonPath("$.size").value(20))
                .andExpect(jsonPath("$.restaurants[*].name", contains("Anand Stall", "Bombay Canteen", "Cafe Madras")))
                .andExpect(jsonPath("$.restaurants[0].cuisines", contains("Street Food")))
                .andExpect(jsonPath("$.restaurants[0].rating.average", nullValue())).andExpect(jsonPath("$.restaurants[0].rating.count").value(0))
                .andExpect(jsonPath("$.restaurants[1].cuisines", contains("Maharashtrian", "North Indian")))
                .andExpect(jsonPath("$.restaurants[1].rating.average").value(4.3)).andExpect(jsonPath("$.restaurants[1].rating.count").value(3))
                .andExpect(jsonPath("$.restaurants[2].cuisines", contains("Desserts", "South Indian")))
                .andExpect(jsonPath("$.restaurants[2].rating.average").value(4.0)).andExpect(jsonPath("$.restaurants[2].rating.count").value(2));
    }

    @Test
    void theCityIsMatchedInAnyCase() throws Exception {
        mvc.perform(get("/restaurants").param("city", "MUMBAI")).andExpect(status().isOk())
                .andExpect(jsonPath("$.city").value("mumbai")).andExpect(jsonPath("$.restaurants", hasSize(3)));
    }

    @Test
    void puneComesInPages() throws Exception {
        mvc.perform(get("/restaurants").param("city", "pune").param("size", "50")).andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurants", hasSize(50))).andExpect(jsonPath("$.restaurants[0].name").value("Pune Kitchen 01"))
                .andExpect(jsonPath("$.restaurants[49].name").value("Pune Kitchen 50"));
        mvc.perform(get("/restaurants").param("city", "pune").param("size", "50").param("page", "1")).andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurants", hasSize(10))).andExpect(jsonPath("$.restaurants[0].name").value("Pune Kitchen 51"));
    }

    @Test
    void aCityWithNoRestaurantsOrAPagePastTheEndIsEmpty() throws Exception {
        mvc.perform(get("/restaurants").param("city", "nagpur")).andExpect(status().isOk()).andExpect(jsonPath("$.restaurants", empty()));
        mvc.perform(get("/restaurants").param("city", "mumbai").param("page", "5")).andExpect(status().isOk()).andExpect(jsonPath("$.restaurants", empty()));
    }

    @Test
    void aCityTiffinoDoesNotServeIs404() throws Exception {
        mvc.perform(get("/restaurants").param("city", "jaipur")).andExpect(status().isNotFound())
                .andExpect(jsonPath("$.detail").value("Tiffino does not deliver in jaipur yet"));
    }

    @Test
    void badParametersAre400() throws Exception {
        mvc.perform(get("/restaurants")).andExpect(status().isBadRequest());
        mvc.perform(get("/restaurants").param("city", "pu")).andExpect(status().isBadRequest());
        mvc.perform(get("/restaurants").param("city", "pune'--")).andExpect(status().isBadRequest());
        mvc.perform(get("/restaurants").param("city", "pune").param("size", "0")).andExpect(status().isBadRequest());
        mvc.perform(get("/restaurants").param("city", "pune").param("size", "51")).andExpect(status().isBadRequest());
        mvc.perform(get("/restaurants").param("city", "pune").param("page", "-1")).andExpect(status().isBadRequest());
        mvc.perform(get("/restaurants").param("city", "pune").param("page", "two")).andExpect(status().isBadRequest());
    }
}
