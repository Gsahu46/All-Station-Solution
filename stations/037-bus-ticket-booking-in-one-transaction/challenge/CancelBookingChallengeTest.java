package com.safarbus.bookings;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /bookings/{id} cancels a booking: its passengers and the booking row go in one transaction
 * (children first, because of the foreign key), and the seats can be booked again. 204, or 404 if there is no such
 * booking.
 */
class CancelBookingChallengeTest extends ApiTest {

    @Test
    void cancellingFreesTheSeats() throws Exception {
        book(BookingContractTest.TWO).andExpect(status().isCreated());
        mvc.perform(delete("/bookings/1")).andExpect(status().isNoContent());
        assertThat(bookings()).isZero();
        assertThat(passengers()).isZero();
        book(BookingContractTest.TWO).andExpect(status().isCreated());
    }

    @Test
    void anUnknownBookingIs404() throws Exception {
        mvc.perform(delete("/bookings/999")).andExpect(status().isNotFound());
    }
}
