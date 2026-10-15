package com.ghoomo.rooms;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /rooms/{id}/blocks/{blockId} releases a hold: 204, and its nights are free again. A block that
 * does not exist, or belongs to another room, is 404.
 */
class CancelBlockChallengeTest extends ApiTest {

    @Test
    void cancellingFreesTheNights() throws Exception {
        mvc.perform(delete("/rooms/101/blocks/1")).andExpect(status().isNoContent());   // Asha's 10-12 June
        mvc.perform(get("/rooms/101/availability").param("from", "2026-06-10").param("to", "2026-06-12"))
                .andExpect(jsonPath("$.nights[*].available", contains(true, true)));
    }

    @Test
    void aBlockOfAnotherRoomOrNoneIs404() throws Exception {
        mvc.perform(delete("/rooms/102/blocks/1")).andExpect(status().isNotFound());
        mvc.perform(delete("/rooms/101/blocks/999")).andExpect(status().isNotFound());
    }
}
