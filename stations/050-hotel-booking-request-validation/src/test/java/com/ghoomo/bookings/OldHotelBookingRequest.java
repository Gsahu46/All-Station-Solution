package com.ghoomo.bookings;

import jakarta.validation.constraints.FutureOrPresent;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

import java.time.LocalDate;

/**
 * The request as it shipped, kept only in tests: every field checked on its own, carefully, and nothing that looks
 * at two fields at once.
 */
record OldHotelBookingRequest(
        @NotNull Long hotelId,
        @NotBlank String roomType,
        @NotNull @FutureOrPresent LocalDate checkIn,
        @NotNull @FutureOrPresent LocalDate checkOut,
        @NotNull @Min(1) @Max(10) Integer adults,
        @Min(0) @Max(10) Integer children,
        @NotBlank String guestName,
        @NotBlank @Pattern(regexp = "[6-9][0-9]{9}") String phone) {
}
