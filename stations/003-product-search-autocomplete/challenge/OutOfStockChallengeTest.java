package com.kartwala.search;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 2: Saffola Gold Oil 1L (id 8) is out of stock. Hide it unless the app asks for out-of-stock items. */
class OutOfStockChallengeTest extends ApiTest {

    @Test
    void outOfStockProductsAreHiddenByDefault() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "saf"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Safari Suitcase Medium")));
    }

    @Test
    void theAppCanAskForThemAndSeesWhichAreOutOfStock() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "saf").param("includeOutOfStock", "true"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Saffola Gold Oil 1L", "Safari Suitcase Medium")))
                .andExpect(jsonPath("$.suggestions[0].inStock").value(false))
                .andExpect(jsonPath("$.suggestions[1].inStock").value(true));
    }

    @Test
    void hidingHappensBeforeTheLimitSoTheListStaysFull() throws Exception {
        // Saffola (8800) would be third. Filtered after the limit, the app would get only two suggestions.
        mvc.perform(get("/suggestions").param("prefix", "sa").param("limit", "3"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Samsung Galaxy M35 5G", "Tata Salt 1kg", "Samsung Galaxy S24")));
    }
}
