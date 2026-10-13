package com.fitnest.classes;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

/** Challenge 2: body of PATCH /classes/{id}. Only the field that changes. */
public record CapacityRequest(@NotNull @Min(1) @Max(50) Integer capacity) {
}
