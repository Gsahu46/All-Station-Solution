package com.rydo.fares;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: estimates for every vehicle type from two points, and the refusals. */
class FareEstimateContractTest extends ApiTest {

    static final String MG_ROAD = "12.9756,77.6066", KORAMANGALA = "12.9352,77.6245";

    /** One vehicle's fare, looked up by name, so a new vehicle type added later does not break these tests. */
    static String fareOf(String vehicle) {
        return "$.estimates[?(@.vehicle == '" + vehicle + "')].farePaise";
    }

    @Test
    void everyVehicleTypeGetsAnEstimateFromTheServersDistance() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", MG_ROAD).param("drop", KORAMANGALA))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.distanceKm").value(6.4))
                .andExpect(jsonPath(fareOf("BIKE"), contains(5800)))
                .andExpect(jsonPath(fareOf("AUTO"), contains(9600)))
                .andExpect(jsonPath(fareOf("CAB"), contains(14000)))
                .andExpect(jsonPath(fareOf("CAB_XL"), contains(20800)));
    }

    @Test
    void aVeryShortRidePaysEachMinimum() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", MG_ROAD).param("drop", MG_ROAD))
                .andExpect(jsonPath("$.distanceKm").value(0.0))
                .andExpect(jsonPath(fareOf("BIKE"), contains(3000)))
                .andExpect(jsonPath(fareOf("AUTO"), contains(3000)))
                .andExpect(jsonPath(fareOf("CAB"), contains(8000)))
                .andExpect(jsonPath(fareOf("CAB_XL"), contains(12000)));
    }

    @Test
    void distanceOrFareSentByTheClientIsIgnored() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", MG_ROAD).param("drop", KORAMANGALA)
                        .param("distanceKm", "1").param("fare", "10"))
                .andExpect(jsonPath("$.distanceKm").value(6.4))
                .andExpect(jsonPath(fareOf("CAB"), contains(14000)));
    }

    @Test
    void aMalformedOrMissingLocationIs400() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", "MG Road").param("drop", KORAMANGALA))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Invalid location"));
        mvc.perform(get("/fare-estimates").param("pickup", "95.0,77.6").param("drop", KORAMANGALA)).andExpect(status().isBadRequest());
        mvc.perform(get("/fare-estimates").param("pickup", MG_ROAD)).andExpect(status().isBadRequest());
    }

    @Test
    void aPointOutsideTheServiceAreaIs422() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", MG_ROAD).param("drop", "19.0760,72.8777"))   // Mumbai
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.title").value("Outside service area"));
    }
}
