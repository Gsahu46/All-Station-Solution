package com.fitnest.classes;

import java.time.LocalDate;
import java.time.LocalTime;

/** A scheduled class. Times are local to the gym (India Standard Time). spotsLeft is worked out per response. */
public record GymClass(long id, String name, String trainer, LocalDate date, LocalTime startTime, int capacity, int spotsLeft) {

    GymClass withSpotsLeft(int spots) {
        return new GymClass(id, name, trainer, date, startTime, capacity, spots);
    }
}
