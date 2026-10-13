package com.tijori.beneficiaries;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

import java.net.URI;
import java.util.Map;
import java.util.TreeMap;

/** Centralised error handling: every error is a ProblemDetail. */
@RestControllerAdvice
class ApiErrors extends ResponseEntityExceptionHandler {

    static final String TYPES = "https://tijori.example/problems/";

    static ProblemDetail problem(HttpStatus status, String type, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setType(URI.create(TYPES + type));
        p.setTitle(title);
        return p;
    }

    @ExceptionHandler
    ResponseEntity<ProblemDetail> notFound(Exceptions.BeneficiaryNotFound e) {
        return respond(problem(HttpStatus.NOT_FOUND, "beneficiary-not-found", "Beneficiary not found",
                "No beneficiary with this id on your account."));
    }

    @ExceptionHandler
    ResponseEntity<ProblemDetail> duplicate(Exceptions.DuplicateBeneficiary e) {
        ProblemDetail p = problem(HttpStatus.CONFLICT, "duplicate-beneficiary", "Already a beneficiary",
                "This account at this branch is already one of your beneficiaries.");
        p.setProperty("existingBeneficiaryId", e.existingId);
        return respond(p);
    }

    /** Both are IFSC problems, so one handler keeps it simple. */
    @ExceptionHandler({Exceptions.UnknownIfsc.class, Exceptions.IfscDirectoryUnavailable.class})
    ResponseEntity<ProblemDetail> ifsc(RuntimeException e) {
        return respond(problem(HttpStatus.BAD_REQUEST, "unknown-ifsc", "Unknown IFSC",
                "We could not verify this IFSC. Please check it and try again."));
    }

    /** Helpful for debugging: the client sees what went wrong. */
    @ExceptionHandler
    ResponseEntity<ProblemDetail> unexpected(Exception e) {
        return respond(problem(HttpStatus.INTERNAL_SERVER_ERROR, "internal-error", "Something went wrong", e.getMessage()));
    }

    /** Shows the user exactly which value was wrong. */
    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        Map<String, String> errors = new TreeMap<>();
        ex.getBindingResult().getFieldErrors().forEach(f ->
                errors.putIfAbsent(f.getField(), "'" + f.getRejectedValue() + "' " + f.getDefaultMessage()));
        ProblemDetail p = problem(HttpStatus.BAD_REQUEST, "invalid-request", "Invalid request", "Some fields are invalid.");
        p.setProperty("errors", errors);
        return handleExceptionInternal(ex, p, headers, status, request);
    }

    private static ResponseEntity<ProblemDetail> respond(ProblemDetail p) {
        return ResponseEntity.status(p.getStatus()).body(p);
    }
}
