package com.ghoomo.bookings;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validator;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/** Checks that a booking request adds up, then records it. A request record only: no room is held, nothing is paid. */
@Service
class BookingDesk {

    record BookingView(long id, long hotelId, String hotelName, String roomType, LocalDate checkIn, LocalDate checkOut,
                       long nights, int adults, int children, String guestName, String phone, String gstin, String status) {
    }

    private final Validator validator;
    private final HotelCatalog catalog;
    private final Map<Long, BookingView> bookings = new ConcurrentHashMap<>();   // shortcut: in memory, lost on restart; a real desk uses a table
    private final AtomicLong ids = new AtomicLong();

    BookingDesk(Validator validator, HotelCatalog catalog) {
        this.validator = validator;
        this.catalog = catalog;
    }

    /** Called after @Valid passed: every field is well-formed. Now the fields must agree with each other. */
    BookingView request(HotelBookingRequest r) {
        Set<ConstraintViolation<HotelBookingRequest>> violations = validator.validate(r, Consistency.class);
        if (!violations.isEmpty()) {
            Map<String, String> errors = new TreeMap<>();
            violations.forEach(v -> errors.merge(v.getPropertyPath().toString(), v.getMessage(), (a, b) -> a + "; " + b));
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT, "Each field is valid, but together they are not a possible booking.");
            p.setTitle("Booking does not add up");
            p.setProperty("errors", errors);
            throw new ErrorResponseException(HttpStatus.UNPROCESSABLE_CONTENT, p, null);
        }
        HotelCatalog.Hotel hotel = catalog.find(r.hotelId()).orElseThrow();   // RoomFitsGuests checked it exists
        long id = ids.incrementAndGet();
        BookingView booking = new BookingView(id, hotel.id(), hotel.name(), HotelCatalog.roomType(r.roomType()), r.checkIn(), r.checkOut(),
                ChronoUnit.DAYS.between(r.checkIn(), r.checkOut()), r.adults(), r.childrenOrZero(), r.guestName().strip(),
                IndianMobile.Validator.digits(r.phone()), r.gstin() == null ? null : r.gstin().strip().toUpperCase(java.util.Locale.ROOT), "REQUESTED");
        bookings.put(id, booking);
        return booking;
    }

    Optional<BookingView> find(long id) {
        return Optional.ofNullable(bookings.get(id));
    }
}
