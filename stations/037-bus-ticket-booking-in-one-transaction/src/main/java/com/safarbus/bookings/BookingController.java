package com.safarbus.bookings;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.sql.SQLException;
import java.util.List;
import java.util.stream.Collectors;

@RestController
class BookingController {

    record BookingRequest(@NotNull Long tripId,
                          @NotNull @Pattern(regexp = "[6-9]\\d{9}", message = "must be a 10-digit Indian mobile number") String contactPhone,
                          @NotNull @Size(min = 1, max = 6) List<@NotNull @Valid Passenger> passengers) {
    }

    record BookingResponse(long bookingId, long tripId, List<Integer> seats, long totalPaise, String status) {
    }

    private final Trips trips;
    private final BookingStore store;

    BookingController(Trips trips, BookingStore store) {
        this.trips = trips;
        this.store = store;
    }

    /** Records a booking (a demo booking record; no payment is taken). */
    @PostMapping("/bookings")
    @ResponseStatus(HttpStatus.CREATED)
    BookingResponse book(@Valid @RequestBody BookingRequest request) throws SQLException {
        Trip trip = trips.find(request.tripId()).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Trip not found", "No trip " + request.tripId() + "."));
        List<Integer> seats = request.passengers().stream().map(Passenger::seatNo).toList();
        if (seats.stream().distinct().count() != seats.size()) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Same seat twice", "Each passenger needs a different seat.");
        }
        if (seats.stream().anyMatch(s -> s > trip.seats())) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "No such seat", "Trip " + trip.id() + " has seats 1 to " + trip.seats() + ".");
        }
        try {
            long bookingId = store.save(trip, request.contactPhone(), request.passengers());
            return new BookingResponse(bookingId, trip.id(), seats, trip.farePaise() * seats.size(), "CONFIRMED");
        } catch (SQLException e) {
            if (BookingStore.violates(e, "booking_passengers_seat_once")) {
                // The database decided, so two people racing for one seat cannot both win.
                List<Integer> taken = store.taken(trip.id(), seats);
                String which = taken.stream().map(String::valueOf).collect(Collectors.joining(", "));
                throw problem(HttpStatus.CONFLICT, "Seat already booked", (taken.size() == 1 ? "Seat " + which + " is" : "Seats " + which + " are")
                        + " already booked on trip " + trip.id() + ". Nothing was booked.");
            }
            throw e;
        }
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
