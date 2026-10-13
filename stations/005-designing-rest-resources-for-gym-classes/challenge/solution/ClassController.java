package com.fitnest.classes;

import jakarta.validation.Valid;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

/**
 * URLs name things (nouns); the HTTP method says what to do with them. Each outcome has its own status code:
 * 200 here it is, 201 created, 204 done with nothing to return, 404 no such thing, 409 conflicts with the current state.
 */
@RestController
class ClassController {

    private final ClassSchedule schedule;

    ClassController(ClassSchedule schedule) {
        this.schedule = schedule;
    }

    /** A filter on a collection is a query parameter: /classes?date=2026-10-19. */
    @GetMapping("/classes")
    List<GymClass> classes(@RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        return schedule.on(date);
    }

    /** A booking is created under the class it is for: the class is in the path, the member in the body. */
    @PostMapping("/classes/{classId}/bookings")
    ResponseEntity<Booking> book(@PathVariable long classId, @Valid @RequestBody BookingRequest request) {
        if (!schedule.memberExists(request.memberId())) {
            throw problem(HttpStatus.BAD_REQUEST, "Unknown member", "No member has the id " + request.memberId() + ".");
        }
        return switch (schedule.book(classId, request.memberId())) {
            case BookingOutcome.Booked(Booking b) -> ResponseEntity.created(URI.create("/bookings/" + b.id())).body(b);
            case BookingOutcome.ClassNotFound() -> throw classNotFound(classId);
            case BookingOutcome.ClassFull() -> throw problem(HttpStatus.CONFLICT, "Class is full", "Every spot in this class is taken.");
            case BookingOutcome.AlreadyBooked(UUID existing) -> throw problem(HttpStatus.CONFLICT, "Already booked",
                    "This member already has booking " + existing + " for this class.");
        };
    }

    /** Challenge 1: the roster is the class's own collection of bookings, so it is nested under the class. */
    @GetMapping("/classes/{classId}/bookings")
    List<Booking> roster(@PathVariable long classId) {
        return schedule.roster(classId).orElseThrow(() -> classNotFound(classId));
    }

    /** Challenge 2: PATCH changes part of the class. 409 when the change conflicts with the bookings already made. */
    @PatchMapping("/classes/{classId}")
    GymClass setCapacity(@PathVariable long classId, @Valid @RequestBody CapacityRequest request) {
        return switch (schedule.setCapacity(classId, request.capacity())) {
            case UPDATED -> schedule.find(classId).orElseThrow();
            case CLASS_NOT_FOUND -> throw classNotFound(classId);
            case BELOW_BOOKINGS -> throw problem(HttpStatus.CONFLICT, "Capacity below bookings",
                    "More members have booked this class than the new capacity allows.");
        };
    }

    /** Once created, a booking is addressed on its own: /bookings/{id}. Nobody needs the class id to find it. */
    @GetMapping("/bookings/{id}")
    Booking booking(@PathVariable UUID id) {
        return schedule.booking(id).orElseThrow(() -> bookingNotFound(id));
    }

    @DeleteMapping("/bookings/{id}")
    ResponseEntity<Void> cancel(@PathVariable UUID id) {
        if (!schedule.cancel(id)) {
            throw bookingNotFound(id);
        }
        return ResponseEntity.noContent().build(); // 204: cancelled, nothing to send back
    }

    @GetMapping("/members/{memberId}/bookings")
    List<Booking> memberBookings(@PathVariable long memberId) {
        if (!schedule.memberExists(memberId)) {
            throw problem(HttpStatus.NOT_FOUND, "Member not found", "No member has the id " + memberId + ".");
        }
        return schedule.forMember(memberId);
    }

    private static ErrorResponseException classNotFound(long classId) {
        return problem(HttpStatus.NOT_FOUND, "Class not found", "No class has the id " + classId + ".");
    }

    private static ErrorResponseException bookingNotFound(UUID id) {
        return problem(HttpStatus.NOT_FOUND, "Booking not found", "No booking has the id " + id + ".");
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail body = ProblemDetail.forStatusAndDetail(status, detail);
        body.setTitle(title);
        return new ErrorResponseException(status, body, null);
    }
}
