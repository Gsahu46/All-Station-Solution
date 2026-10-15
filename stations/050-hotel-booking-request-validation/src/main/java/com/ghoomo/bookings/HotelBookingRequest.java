package com.ghoomo.bookings;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.LocalDate;

/**
 * Field rules (Default group) say each value is well-formed: 400 when broken. Class rules (Consistency group) say
 * the values make sense together: 422 when broken. They are separate so a missing date is never reported as an
 * impossible stay.
 */
@ValidStay(groups = Consistency.class)
@RoomFitsGuests(groups = Consistency.class)
record HotelBookingRequest(
        @NotNull Long hotelId,
        @NotBlank @Size(max = 20) String roomType,
        @NotNull LocalDate checkIn,
        @NotNull LocalDate checkOut,
        @NotNull @Min(1) @Max(10) Integer adults,
        @Min(0) @Max(10) Integer children,
        @NotBlank @Size(max = 80) String guestName,
        @NotBlank @IndianMobile String phone) {

    int childrenOrZero() {
        return children == null ? 0 : children;
    }
}
