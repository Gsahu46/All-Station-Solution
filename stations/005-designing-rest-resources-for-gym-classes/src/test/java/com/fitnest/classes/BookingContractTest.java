package com.fitnest.classes;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.util.UUID;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: every endpoint, every status code, each for its own reason. */
class BookingContractTest extends ApiTest {

    @Test
    void classesForADateAreListedByStartTimeWithSpotsLeft() throws Exception {
        book(1, 101);
        mvc.perform(get("/classes").param("date", "2026-10-19"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("Morning Yoga", "HIIT Blast", "Zumba")))
                .andExpect(jsonPath("$[0].startTime").value("06:30:00"))
                .andExpect(jsonPath("$[0].capacity").value(2))
                .andExpect(jsonPath("$[0].spotsLeft").value(1));
    }

    @Test
    void aDateWithNoClassesIsAnEmptyList() throws Exception {
        mvc.perform(get("/classes").param("date", "2026-12-25"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(0)));
    }

    @Test
    void theDateIsRequiredAndMustBeIso() throws Exception {
        mvc.perform(get("/classes")).andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        mvc.perform(get("/classes").param("date", "19-10-2026")).andExpect(status().isBadRequest());
    }

    @Test
    void bookingIs201WithALocationThatCanBeRead() throws Exception {
        String location = book(2, 101)
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", matchesPattern("/bookings/[0-9a-f-]{36}")))
                .andExpect(jsonPath("$.classId").value(2))
                .andExpect(jsonPath("$.memberId").value(101))
                .andReturn().getResponse().getHeader("Location");
        mvc.perform(get(location)).andExpect(status().isOk()).andExpect(jsonPath("$.classId").value(2));
    }

    @Test
    void aFullClassIs409() throws Exception {
        book(1, 101);
        book(1, 102);
        book(1, 103).andExpect(status().isConflict())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Class is full"));
    }

    @Test
    void bookingTheSameClassTwiceIs409AndNamesTheExistingBooking() throws Exception {
        String location = bookAndGetLocation(3, 101);
        book(3, 101).andExpect(status().isConflict())
                .andExpect(jsonPath("$.title").value("Already booked"))
                .andExpect(jsonPath("$.detail").value(org.hamcrest.Matchers.containsString(location.substring("/bookings/".length()))));
    }

    @Test
    void anUnknownClassIs404() throws Exception {
        book(999, 101).andExpect(status().isNotFound()).andExpect(jsonPath("$.title").value("Class not found"));
    }

    @Test
    void anUnknownOrMissingMemberIs400() throws Exception {
        book(2, 999).andExpect(status().isBadRequest()).andExpect(jsonPath("$.title").value("Unknown member"));
        mvc.perform(post("/classes/2/bookings").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.memberId").value("must not be null"));
    }

    @Test
    void cancellingIs204WithNoBodyAndFreesTheSpot() throws Exception {
        String first = bookAndGetLocation(1, 101);
        book(1, 102);
        mvc.perform(delete(first))
                .andExpect(status().isNoContent())
                .andExpect(content().string(""));
        book(1, 103).andExpect(status().isCreated());
    }

    @Test
    void aCancelledBookingIsGone() throws Exception {
        String location = bookAndGetLocation(2, 102);
        mvc.perform(delete(location)).andExpect(status().isNoContent());
        mvc.perform(get(location)).andExpect(status().isNotFound());
        mvc.perform(delete(location)).andExpect(status().isNotFound())  // nothing left to cancel (station 008 revisits repeat deletes)
                .andExpect(jsonPath("$.title").value("Booking not found"));
    }

    @Test
    void aMembersBookingsAreANestedCollection() throws Exception {
        book(2, 103);
        book(4, 103);
        book(2, 101);
        mvc.perform(get("/members/103/bookings"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[*].classId", contains(2, 4)));
        mvc.perform(get("/members/102/bookings")).andExpect(status().isOk()).andExpect(jsonPath("$", hasSize(0)));
        mvc.perform(get("/members/999/bookings")).andExpect(status().isNotFound());
    }

    @Test
    void theOldVerbUrlsAndWrongMethodsAreNotPartOfTheApi() throws Exception {
        mvc.perform(post("/bookClass").param("classId", "1").param("memberId", "101")).andExpect(status().isNotFound());
        mvc.perform(post("/cancelBooking")).andExpect(status().isNotFound());
        mvc.perform(put("/bookings/{id}", UUID.randomUUID())).andExpect(status().isMethodNotAllowed());
    }
}
