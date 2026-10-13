package com.fitnest.classes;

import java.time.Instant;
import java.util.UUID;

/** One member's place in one class. A resource of its own, with its own URL: /bookings/{id}. */
public record Booking(UUID id, long classId, long memberId, Instant bookedAt) {
}
