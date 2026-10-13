package com.parkora.parking;

import java.time.Instant;
import java.util.UUID;

/** Given at the exit gate. Stored with the ticket, so asking again returns exactly the same receipt. */
public record Receipt(UUID ticketId, String vehicleNumber, String slotId, Instant enteredAt, Instant exitedAt,
                      long minutesParked, long hoursCharged, long feePaise) {
}
