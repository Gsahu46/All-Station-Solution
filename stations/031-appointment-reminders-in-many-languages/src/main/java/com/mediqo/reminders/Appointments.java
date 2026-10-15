package com.mediqo.reminders;

import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.Optional;

/** Demo appointments in memory. Each patient has a preferred language for reminders. */
@Component
class Appointments {

    record Appointment(long id, String patient, String doctor, LocalDateTime at, long amountPaise, String preferredLanguage) {
    }

    private final Map<Long, Appointment> byId = Map.of(
            501L, new Appointment(501, "Asha", "Mehta", LocalDateTime.of(2026, 10, 20, 10, 30), 12_345_650, "hi"),
            502L, new Appointment(502, "Ravi", "Iyer", LocalDateTime.of(2026, 10, 21, 15, 0), 50_000, "en"));

    Optional<Appointment> find(long id) {
        return Optional.ofNullable(byId.get(id));
    }
}
