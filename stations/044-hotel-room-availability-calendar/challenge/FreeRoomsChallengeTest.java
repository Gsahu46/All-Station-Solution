package com.ghoomo.rooms;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: GET /rooms/free?checkIn&checkOut&guests: every room with enough capacity and no night held in the
 * range, by id. One query: rooms where NOT EXISTS an overlapping block, with the same half-open rule.
 */
class FreeRoomsChallengeTest extends ApiTest {

    @Test
    void roomsFreeForTheWholeStayWithEnoughBeds() throws Exception {
        mvc.perform(get("/rooms/free").param("checkIn", "2026-06-11").param("checkOut", "2026-06-13").param("guests", "2"))
                .andExpect(jsonPath("$[*].id", contains(102)));
        mvc.perform(get("/rooms/free").param("checkIn", "2026-06-12").param("checkOut", "2026-06-14").param("guests", "2"))
                .andExpect(jsonPath("$[*].id", contains(101, 102)));
        mvc.perform(get("/rooms/free").param("checkIn", "2026-06-12").param("checkOut", "2026-06-14").param("guests", "5"))
                .andExpect(jsonPath("$", empty()));
    }
}
