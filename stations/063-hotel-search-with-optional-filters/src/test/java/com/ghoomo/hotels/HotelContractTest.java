package com.ghoomo.hotels;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class HotelContractTest extends ApiTest {

    @Test
    void noFiltersListsEveryHotelCheapestFirst() throws Exception {
        mvc.perform(get("/hotels")).andExpect(status().isOk())
                .andExpect(jsonPath("$.total").value(9)).andExpect(jsonPath("$.sort").value("price"))
                .andExpect(jsonPath("$.hotels[0].name").value("Anjuna Hostel")).andExpect(jsonPath("$.hotels[0].pricePerNightPaise").value(90000))
                .andExpect(jsonPath("$.hotels[8].name").value("Rambagh Court"));
    }

    @Test
    void goaWithWifiAndPoolUnderRs5000() throws Exception {
        mvc.perform(get("/hotels").param("city", "Goa").param("amenities", "wifi,POOL").param("maxPrice", "5000")).andExpect(status().isOk())
                .andExpect(jsonPath("$.total").value(2))
                .andExpect(jsonPath("$.hotels[*].name", contains("Calangute Sands", "Candolim Palms")))
                .andExpect(jsonPath("$.hotels[0].amenities", contains("breakfast", "pool", "wifi")));
    }

    @Test
    void everyAmenityMustMatchAndEachHotelAppearsOnce() throws Exception {
        mvc.perform(get("/hotels").param("amenities", "wifi,breakfast")).andExpect(status().isOk())
                .andExpect(jsonPath("$.hotels[*].name", contains("Calangute Sands", "Pink City Haveli", "Panjim Heritage", "Fort Aguada Resort")));
    }

    @Test
    void starsPriceRangeAndSort() throws Exception {
        mvc.perform(get("/hotels").param("city", "jaipur").param("stars", "4,5").param("sort", "-price")).andExpect(status().isOk())
                .andExpect(jsonPath("$.hotels[*].name", contains("Rambagh Court", "Pink City Haveli")));
        mvc.perform(get("/hotels").param("minPrice", "3000").param("maxPrice", "5000")).andExpect(status().isOk())
                .andExpect(jsonPath("$.hotels[*].name", contains("Amber View", "Calangute Sands", "Candolim Palms")));
    }

    @Test
    void pagesFollowTheSortWithoutGapsOrRepeats() throws Exception {
        mvc.perform(get("/hotels").param("sort", "-stars").param("size", "2").param("page", "1")).andExpect(status().isOk())
                .andExpect(jsonPath("$.total").value(9))
                .andExpect(jsonPath("$.hotels[*].name", contains("Candolim Palms", "Pink City Haveli")));
    }

    @Test
    void noMatchIsAnEmptyPage() throws Exception {
        mvc.perform(get("/hotels").param("city", "shimla")).andExpect(status().isOk())
                .andExpect(jsonPath("$.total").value(0)).andExpect(jsonPath("$.hotels", empty()));
    }

    @Test
    void anythingOutsideTheRulesIs400() throws Exception {
        mvc.perform(get("/hotels").param("sort", "price_per_night_paise")).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("Sort by one of [-price, -stars, name, price, stars]"));
        mvc.perform(get("/hotels").param("amenities", "wifi,sauna")).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("Unknown amenities [sauna]"));
        mvc.perform(get("/hotels").param("minPrice", "6000").param("maxPrice", "5000")).andExpect(status().isBadRequest());
        mvc.perform(get("/hotels").param("stars", "6")).andExpect(status().isBadRequest());
        mvc.perform(get("/hotels").param("city", "goa' OR '1'='1")).andExpect(status().isBadRequest());
        mvc.perform(get("/hotels").param("minPrice", "cheap")).andExpect(status().isBadRequest());
        mvc.perform(get("/hotels").param("size", "0")).andExpect(status().isBadRequest());
    }

    @Test
    void aSortThatLooksLikeSqlIsRefusedAndRunsNothing() throws Exception {
        mvc.perform(get("/hotels").param("sort", "name; DELETE FROM hotel_amenities")).andExpect(status().isBadRequest());
        assertThat(jdbc.sql("SELECT count(*) FROM hotel_amenities").query(Long.class).single()).isEqualTo(20);
    }
}
