package com.ghoomo.rooms;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

@RestController
class RoomController {

    /** Demo limits: a calendar shows up to 62 nights, a stay is up to 30 nights. */
    static final int MAX_CALENDAR_NIGHTS = 62;
    static final int MAX_STAY_NIGHTS = 30;

    record NewBlock(@NotNull LocalDate checkIn, @NotNull LocalDate checkOut, @NotBlank @Size(max = 80) String guestName) {
    }

    private final Availability availability;

    RoomController(Availability availability) {
        this.availability = availability;
    }

    @GetMapping("/rooms/{id}/availability")
    Availability.Calendar availability(@PathVariable long id,
                                       @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                       @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        requireRange(from, to, MAX_CALENDAR_NIGHTS, "to");
        return availability.calendar(id, from, to);
    }

    /** Holds a room for a stay (a demo hold record; no payment, no confirmation sent). */
    @PostMapping("/rooms/{id}/blocks")
    @ResponseStatus(HttpStatus.CREATED)
    Availability.BlockView block(@PathVariable long id, @Valid @RequestBody NewBlock request) {
        requireRange(request.checkIn(), request.checkOut(), MAX_STAY_NIGHTS, "checkOut");
        return availability.block(id, request.checkIn(), request.checkOut(), request.guestName().strip());
    }

    private static void requireRange(LocalDate start, LocalDate end, int maxNights, String endName) {
        if (end.isBefore(start)) {   // PR: "allow same-day stays for day rooms"
            throw Availability.problem(HttpStatus.BAD_REQUEST, "Invalid dates", endName + " must be after the start: the last date is the morning you leave.");
        }
        if (ChronoUnit.DAYS.between(start, end) > maxNights) {
            throw Availability.problem(HttpStatus.BAD_REQUEST, "Invalid dates", "At most " + maxNights + " nights.");
        }
    }
}
