package com.parkora.parking;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: the display board at the gate: free slots per floor, per type. */
class AvailabilityBoardChallengeTest extends ApiTest {

    @Test
    void anEmptyBuildingShowsEveryFloorFull() throws Exception {
        mvc.perform(get("/parking/availability"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(6)))
                .andExpect(jsonPath("$[*].floor", contains(0, 1, 2, 3, 4, 5)))
                .andExpect(jsonPath("$[0].freeCarSlots").value(40))
                .andExpect(jsonPath("$[0].freeBikeSlots").value(20));
    }

    @Test
    void parkedVehiclesAreSubtractedFromTheirFloorAndType() throws Exception {
        enter("MH12AB0001", "CAR");
        enter("MH12AB0002", "CAR");
        String bike = ticketOf(enter("MH12AB0003", "BIKE"));
        exit(bike);
        mvc.perform(get("/parking/availability"))
                .andExpect(jsonPath("$[0].freeCarSlots").value(38))
                .andExpect(jsonPath("$[0].freeBikeSlots").value(20))
                .andExpect(jsonPath("$[1].freeCarSlots").value(40));
    }
}
