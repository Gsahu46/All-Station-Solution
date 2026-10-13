package com.rydo.fares;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: trips to the airport (latitude 13.18 to 13.22, longitude 77.68 to 77.73, a demo box) pay a Rs 120
 * toll in cars, not on bikes or autos.
 */
class AirportTollChallengeTest extends ApiTest {

    static final String MG_ROAD = "12.9756,77.6066", AIRPORT = "13.1986,77.7066";

    @Test
    void carsToTheAirportPayTheTollBikesAndAutosDoNot() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", MG_ROAD).param("drop", AIRPORT))
                .andExpect(jsonPath("$.distanceKm").value(35.2))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'CAB')].farePaise", contains(54300 + 12000)))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'CAB_XL')].farePaise", contains(78400 + 12000)))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'AUTO')].farePaise", contains(52800)))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'BIKE')].farePaise", contains(23100)));
    }

    @Test
    void tripsElsewhereHaveNoToll() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", MG_ROAD).param("drop", "12.9352,77.6245"))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'CAB')].farePaise", contains(14000)));
    }
}
