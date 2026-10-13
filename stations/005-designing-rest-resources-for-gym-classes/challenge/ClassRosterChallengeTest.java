package com.fitnest.classes;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: the trainer's roster, GET /classes/{id}/bookings: who booked this class, in booking order. */
class ClassRosterChallengeTest extends ApiTest {

    @Test
    void theRosterListsTheClassBookingsInTheOrderTheyWereMade() throws Exception {
        book(3, 102);
        book(2, 101);
        book(3, 101);
        mvc.perform(get("/classes/3/bookings"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[*].memberId", contains(102, 101)));
    }

    @Test
    void aClassNobodyBookedHasAnEmptyRoster() throws Exception {
        mvc.perform(get("/classes/4/bookings")).andExpect(status().isOk()).andExpect(jsonPath("$", hasSize(0)));
    }

    @Test
    void anUnknownClassIs404() throws Exception {
        mvc.perform(get("/classes/999/bookings")).andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("Class not found"));
    }
}
