package com.parkora.parking;

import java.time.Instant;
import java.util.UUID;

/** Given at the entry gate: which slot to drive to, and when the clock started. */
public record Ticket(UUID ticketId, String vehicleNumber, VehicleType vehicleType, Slot slot, Instant enteredAt) {
}
