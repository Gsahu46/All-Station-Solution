package com.fitnest.classes;

import java.util.UUID;

/**
 * Everything that can happen when a member books. The schedule says what happened; the controller decides
 * which status code means that. Keeping the two apart is what lets each outcome get its own code.
 */
sealed interface BookingOutcome {

    record Booked(Booking booking) implements BookingOutcome {
    }

    record ClassNotFound() implements BookingOutcome {
    }

    record ClassFull() implements BookingOutcome {
    }

    record AlreadyBooked(UUID existingBookingId) implements BookingOutcome {
    }
}
