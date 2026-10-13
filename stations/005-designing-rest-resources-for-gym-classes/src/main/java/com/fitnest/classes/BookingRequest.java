package com.fitnest.classes;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

/** Body of POST /classes/{id}/bookings. The class comes from the URL, so it is not repeated here. */
public record BookingRequest(@NotNull @Positive Long memberId) {
}
