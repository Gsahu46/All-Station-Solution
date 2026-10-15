package com.ghoomo.rooms;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract. Room 101: held 10-12 June and 15-16 June. */
class AvailabilityContractTest extends ApiTest {

    @Test
    void theCalendarShowsEachNight() throws Exception {
        mvc.perform(get("/rooms/101/availability").param("from", "2026-06-09").param("to", "2026-06-17")).andExpect(status().isOk())
                .andExpect(jsonPath("$.nights[*].date", contains("2026-06-09", "2026-06-10", "2026-06-11", "2026-06-12", "2026-06-13", "2026-06-14", "2026-06-15", "2026-06-16")))
                .andExpect(jsonPath("$.nights[*].available", contains(true, false, false, true, true, true, false, true)))
                .andExpect(jsonPath("$.freeNights").value(5));
    }

    @Test
    void aFreeStayIsHeldAndAnOverlappingOneIsNot() throws Exception {
        hold(101, "2026-06-12", "2026-06-15").andExpect(status().isCreated())
                .andExpect(jsonPath("$.nights").value(3)).andExpect(jsonPath("$.roomId").value(101));
        hold(101, "2026-06-11", "2026-06-13").andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Not available"));
        hold(102, "2026-06-11", "2026-06-13").andExpect(status().isCreated());   // another room, same nights
    }

    @Test
    void anUnknownRoomIs404() throws Exception {
        hold(999, "2026-07-01", "2026-07-02").andExpect(status().isNotFound()).andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        mvc.perform(get("/rooms/999/availability").param("from", "2026-06-09").param("to", "2026-06-10")).andExpect(status().isNotFound());
    }

    @Test
    void impossibleDatesAre400() throws Exception {
        hold(101, "2026-07-02", "2026-07-02").andExpect(status().isBadRequest());   // zero nights
        hold(101, "2026-07-03", "2026-07-01").andExpect(status().isBadRequest());
        hold(101, "2026-07-01", "2026-08-15").andExpect(status().isBadRequest());   // over 30 nights
        mvc.perform(get("/rooms/101/availability").param("from", "2026-06-10").param("to", "2026-06-10")).andExpect(status().isBadRequest());
        mvc.perform(post("/rooms/101/blocks").contentType(MediaType.APPLICATION_JSON)
                .content("{\"checkIn\":\"2026-07-01\",\"checkOut\":\"2026-07-02\"}")).andExpect(status().isBadRequest());
        mvc.perform(post("/rooms/101/blocks").contentType(MediaType.APPLICATION_JSON)
                .content("{\"checkIn\":\"2026-07-01\",\"checkOut\":\"2026-07-02\",\"guestName\":\"A\",\"nights\":5}")).andExpect(status().isBadRequest());
    }
}
