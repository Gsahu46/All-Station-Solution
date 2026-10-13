package com.tiffino.menu;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.everyItem;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.lessThanOrEqualTo;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: defaults, each filter, combinations, and every way a request can be wrong. */
class MenuContractTest extends ApiTest {

    @Test
    void noFiltersReturnsEveryDishMostOrderedFirst() throws Exception {
        mvc.perform(get("/restaurants/101/menu"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.restaurantId").value(101))
                .andExpect(jsonPath("$.restaurantName").value("Annapoorna Mess"))
                .andExpect(jsonPath("$.dishes", hasSize(14)))
                .andExpect(jsonPath("$.dishes[0].name").value("Chicken Biryani"))
                .andExpect(jsonPath("$.dishes[0].pricePaise").value(28000))
                .andExpect(jsonPath("$.dishes[1].name").value("Masala Dosa"));
    }

    @Test
    void vegUnder200CheapestFirstIsTheCustomersQuestion() throws Exception {
        mvc.perform(get("/restaurants/101/menu")
                        .param("veg", "true").param("maxPrice", "200").param("sort", "price_asc").param("limit", "5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes[*].veg", everyItem(org.hamcrest.Matchers.is(true))))
                .andExpect(jsonPath("$.dishes[*].pricePaise", everyItem(lessThanOrEqualTo(20000))))
                .andExpect(jsonPath("$.dishes[*].name", contains(
                        "Idli Sambar", "Gulab Jamun (2 pcs)", "Curd Rice", "Lemon Rice", "Masala Dosa")));
    }

    @Test
    void maxPriceIsInclusiveAndInRupees() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("maxPrice", "199").param("sort", "price_desc").param("limit", "1"))
                .andExpect(jsonPath("$.dishes[0].name").value("Veg Thali"))      // Rs 199.00 is "at most Rs 199"
                .andExpect(jsonPath("$.dishes[0].pricePaise").value(19900));
    }

    @Test
    void vegFalseMeansNonVegOnly() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("veg", "false").param("sort", "price_desc"))
                .andExpect(jsonPath("$.dishes[*].name", contains(
                        "Mutton Rogan Josh", "Chicken Biryani", "Fish Fry", "Egg Curry")));
    }

    @Test
    void equalPricesAreOrderedByNameSoTheAnswerNeverChanges() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("maxPrice", "80").param("sort", "price_desc"))
                .andExpect(jsonPath("$.dishes[*].name", contains("Curd Rice", "Lemon Rice", "Gulab Jamun (2 pcs)", "Idli Sambar")));
    }

    @Test
    void noMatchingDishIsAnEmptyListNotAnError() throws Exception {
        mvc.perform(get("/restaurants/102/menu").param("veg", "true"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes", hasSize(0)));
    }

    @Test
    void unknownRestaurantIs404Problem() throws Exception {
        mvc.perform(get("/restaurants/999/menu"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType("application/problem+json"))
                .andExpect(jsonPath("$.title").value("Restaurant not found"));
    }

    @Test
    void outOfRangeFiltersAre400WithOneMessagePerParameter() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("limit", "0").param("maxPrice", "-5").param("sort", "cheapest"))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType("application/problem+json"))
                .andExpect(jsonPath("$.errors.limit").value("must be greater than or equal to 1"))
                .andExpect(jsonPath("$.errors.maxPrice").value("must be greater than or equal to 1"))
                .andExpect(jsonPath("$.errors.sort").value("must be recommended, price_asc or price_desc"));
    }

    @Test
    void limitAbove50Is400() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("limit", "500"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.limit").value("must be less than or equal to 50"));
    }

    @Test
    void valuesOfTheWrongTypeAre400() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("veg", "maybe")).andExpect(status().isBadRequest())
                .andExpect(content().contentType("application/problem+json"));
        mvc.perform(get("/restaurants/101/menu").param("limit", "five")).andExpect(status().isBadRequest());
        mvc.perform(get("/restaurants/abc/menu")).andExpect(status().isBadRequest());
    }
}
