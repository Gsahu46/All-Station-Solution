package com.parkora.parking;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Locale;
import java.util.UUID;
import java.util.regex.Pattern;

@RestController
class ParkingController {

    /** Indian-style plates: MH12AB1234, DL3CAF0001 (a demo rule; it does not cover every real format). */
    private static final Pattern PLATE = Pattern.compile("[A-Z]{2}\\d{1,2}[A-Z]{0,3}\\d{4}");

    record EntryRequest(@NotBlank String vehicleNumber, @NotNull VehicleType vehicleType) {
    }

    private final Garage garage;

    ParkingController(Garage garage) {
        this.garage = garage;
    }

    @PostMapping("/parking/entries")
    @ResponseStatus(HttpStatus.CREATED)
    Ticket enter(@Valid @RequestBody EntryRequest request) {
        // "mh 12 ab-1234" and "MH12AB1234" are the same car. Locale.ROOT so a Turkish server keeps "i" as "I".
        String plate = request.vehicleNumber().replaceAll("[\\s-]", "").toUpperCase(Locale.ROOT);
        if (!PLATE.matcher(plate).matches()) {
            throw new ErrorResponseException(HttpStatus.BAD_REQUEST,
                    problem(HttpStatus.BAD_REQUEST, "Invalid vehicle number", "Use a number plate like MH12AB1234."), null);
        }
        return garage.enter(plate, request.vehicleType());
    }

    @PostMapping("/parking/exits/{ticketId}")
    Receipt exit(@PathVariable UUID ticketId) {
        return garage.exit(ticketId);
    }

    @ExceptionHandler
    ProblemDetail full(Garage.GarageFull e) {
        return problem(HttpStatus.CONFLICT, "No free slot", "Every slot for this vehicle type is taken.");
    }

    @ExceptionHandler
    ProblemDetail alreadyParked(Garage.AlreadyParked e) {
        ProblemDetail p = problem(HttpStatus.CONFLICT, "Already parked", "This vehicle already has an open ticket.");
        p.setProperty("ticketId", e.ticketId);
        return p;
    }

    @ExceptionHandler
    ProblemDetail unknownTicket(Garage.TicketNotFound e) {
        return problem(HttpStatus.NOT_FOUND, "Ticket not found", "No ticket has this id.");
    }

    private static ProblemDetail problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return p;
    }
}
