package com.ghoomo.bookings;

import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: the two bookings from the support tickets, through the old request's
 * field-by-field rules (with the app's own validator) and through the fixed API.
 */
class FieldByFieldTrapTest extends ApiTest {

    @Autowired
    Validator validator;

    @Test
    void checkOutBeforeCheckInPassesEveryFieldRule() throws Exception {
        var old = new OldHotelBookingRequest(1L, "STANDARD", today().plusDays(33), today().plusDays(30), 2, 0, "Asha Verma", "9876543210");
        assertThat(validator.validate(old)).isEmpty();   // both dates are in the future: each one is "valid"

        book(booking().replace(day(33), "OUT").replace(day(30), day(33)).replace("OUT", day(30)))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.errors.checkOut").value("must be after checkIn: a stay is at least one night"));
    }

    @Test
    void sixGuestsInATwoPersonRoomPassEveryFieldRule() throws Exception {
        var old = new OldHotelBookingRequest(1L, "STANDARD", today().plusDays(30), today().plusDays(33), 4, 2, "Asha Verma", "9876543210");
        assertThat(validator.validate(old)).isEmpty();   // 4 adults is within 1 to 10, 2 children within 0 to 10

        book(booking().replace("\"adults\":2,\"children\":0", "\"adults\":4,\"children\":2"))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.errors.guests").value("6 guests do not fit a STANDARD room, which sleeps 2"));
    }
}
