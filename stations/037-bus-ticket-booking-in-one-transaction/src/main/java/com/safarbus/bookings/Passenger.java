package com.safarbus.bookings;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

record Passenger(@NotBlank @Size(max = 60) String name, @NotNull @Min(0) @Max(120) Integer age, @NotNull @Min(1) Integer seatNo) {
}
