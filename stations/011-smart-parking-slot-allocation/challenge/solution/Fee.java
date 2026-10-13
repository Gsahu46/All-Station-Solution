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

    /** Challenge 2: full days cost the cap each; the rest is charged hourly, at most one more cap. */
    static long feePaise(VehicleType type, Duration parked) {
        long fullDays = parked.toDays();
        Duration rest = parked.minusDays(fullDays);
        long restFee = fullDays > 0 && rest.isZero() ? 0 : Math.min(type.dailyCapPaise, hourly(type, rest));
        return fullDays * type.dailyCapPaise + restFee;
    }

    private static long hourly(VehicleType type, Duration parked) {
        return type.firstHourPaise + (hoursCharged(parked) - 1) * type.extraHourPaise;
    }
}
