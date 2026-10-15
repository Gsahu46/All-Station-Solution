package com.ghoomo.bookings;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

import java.util.Map;
import java.util.TreeMap;

/**
 * Spring already turns an invalid @Valid body into an RFC 9457 problem (the base class). We add an "errors" map,
 * field -> message, so the booking form can show each message next to its input. The 422 for fields that do not add up has the same shape (BookingDesk).
 */
@RestControllerAdvice
class ApiErrors extends ResponseEntityExceptionHandler {

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        Map<String, String> errors = new TreeMap<>();
        ex.getBindingResult().getFieldErrors().forEach(e -> errors.putIfAbsent(e.getField(), e.getDefaultMessage()));
        ex.getBody().setDetail("Some fields are missing or malformed.");
        ex.getBody().setProperty("errors", errors);
        return handleExceptionInternal(ex, null, headers, status, request);
    }
}
