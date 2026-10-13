package com.seatsure.registrations;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.UUID;

@RestController
@RequestMapping("/events/{eventId}/registrations")
class RegistrationController {

    private final RegistrationStore store;

    RegistrationController(RegistrationStore store) {
        this.store = store;
    }

    /** @Valid: the body is checked before this method runs. An invalid body never reaches store.save. */
    @PostMapping
    ResponseEntity<Registration> register(@PathVariable String eventId, @Valid @RequestBody RegistrationRequest request) {
        requireEvent(eventId);
        // Challenge 1: one registration per email per event.
        Registration saved = store.saveIfNew(eventId, request).orElseThrow(() -> {
            ProblemDetail body = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT,
                    "This email is already registered for this event.");
            body.setTitle("Already registered");
            return new ErrorResponseException(HttpStatus.CONFLICT, body, null);
        });
        URI location = URI.create("/events/" + eventId + "/registrations/" + saved.id());
        return ResponseEntity.created(location).body(saved); // 201 Created + Location: where to read it back
    }

    @GetMapping("/{id}")
    Registration get(@PathVariable String eventId, @PathVariable UUID id) {
        requireEvent(eventId);
        return store.find(eventId, id).orElseThrow(() -> notFound("Registration not found", "No registration " + id + " for this event."));
    }

    /** Challenge 2: the organiser's download. A literal path, so Spring never tries to read "export" as a UUID. */
    @GetMapping(value = "/export", produces = "text/csv")
    String export(@PathVariable String eventId) {
        requireEvent(eventId);
        return CsvExport.of(store.forEvent(eventId));
    }

    private void requireEvent(String eventId) {
        if (!store.eventExists(eventId)) {
            throw notFound("Event not found", "No event has the id " + eventId + ".");
        }
    }

    private static ErrorResponseException notFound(String title, String detail) {
        ProblemDetail body = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, detail);
        body.setTitle(title);
        return new ErrorResponseException(HttpStatus.NOT_FOUND, body, null);
    }
}
