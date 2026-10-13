package com.seatsure.registrations;

import java.time.Instant;
import java.util.UUID;

/** A stored registration, and the response body. The server sets id, eventId and registeredAt. */
public record Registration(UUID id, String eventId, String name, String email, String phone, int tickets, Instant registeredAt) {
}
