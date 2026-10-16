package com.dakroute.shipments;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /shipments/{awb} returns {awb, bookedOn, status} for one airway bill number, in any case
 * ("dr1000000002" finds DR1000000002). An unknown number is 404; one that is not DR + 10 digits is 400.
 */
class TrackByAwbChallengeTest extends ApiTest {

    @Test
    void oneShipmentByItsNumber() throws Exception {
        mvc.perform(get("/shipments/dr1000000002")).andExpect(status().isOk())
                .andExpect(jsonPath("$.awb").value("DR1000000002")).andExpect(jsonPath("$.bookedOn").value("2026-03-15")).andExpect(jsonPath("$.status").value("RETURNED"));
    }

    @Test
    void unknownIs404AndMalformedIs400() throws Exception {
        mvc.perform(get("/shipments/DR0000000000")).andExpect(status().isNotFound());
        mvc.perform(get("/shipments/DR12")).andExpect(status().isBadRequest());
    }
}
