package com.ghoomo.bookings;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;

@RestController
class BookingController {

    private final BookingDesk desk;

    BookingController(BookingDesk desk) {
        this.desk = desk;
    }

    /** @Valid runs the Default group only: a broken field stops here with 400, before any cross-field check. */
    @PostMapping("/hotel-bookings")
    ResponseEntity<BookingDesk.BookingView> book(@Valid @RequestBody HotelBookingRequest request) {
        BookingDesk.BookingView booking = desk.request(request);
        return ResponseEntity.created(URI.create("/hotel-bookings/" + booking.id())).body(booking);
    }

    @GetMapping("/hotel-bookings/{id}")
    BookingDesk.BookingView get(@PathVariable long id) {
        return desk.find(id).orElseThrow(() -> {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No booking request " + id + ".");
            p.setTitle("Booking not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        });
    }
}
