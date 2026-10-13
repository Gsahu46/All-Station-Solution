package com.parkora.parking;

import java.time.Duration;

/** The tariff, as plain arithmetic so it can be tested without Spring. */
final class Fee {

    private Fee() {
    }

    /** Every started hour counts: 60:00 is 1 hour, 60:01 is 2. Even a 5-minute stay pays the first hour. */
    static long hoursCharged(Duration parked) {
        return Math.max(1, Math.ceilDiv(parked.toSeconds(), 3600));
    }

    static long feePaise(VehicleType type, Duration parked) {
        return type.firstHourPaise + (hoursCharged(parked) - 1) * type.extraHourPaise;
    }
}
