package com.tijori.beneficiaries;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.TypeMismatchException;
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
import java.util.UUID;

/**
 * Every error from every endpoint leaves through here, as one shape: an RFC 9457 problem
 * (application/problem+json) with type, title, status, detail and instance. The "type" is a stable URI per
 * kind of error, so the app can branch on it: unknown-ifsc means "check the code", ifsc-directory-unavailable
 * means "try again later". Exception messages and stack traces go to the log, never into a response.
 */
@RestControllerAdvice
class ApiErrors extends ResponseEntityExceptionHandler {

    static final String TYPES = "https://tijori.example/problems/";
    private static final Logger log = LoggerFactory.getLogger(ApiErrors.class);

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
        p.setProperty("existingBeneficiaryId", e.existingId); // the customer's own data: safe to return
        return respond(p);
    }

    @ExceptionHandler
    ResponseEntity<ProblemDetail> unknownIfsc(Exceptions.UnknownIfsc e) {
        return respond(problem(HttpStatus.BAD_REQUEST, "unknown-ifsc", "Unknown IFSC",
                "No bank branch has this IFSC. Check the code printed on a cheque or the bank's website."));
    }

    @ExceptionHandler
    ResponseEntity<ProblemDetail> directoryDown(Exceptions.IfscDirectoryUnavailable e) {
        log.warn("IFSC directory unavailable", e);
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .header(HttpHeaders.RETRY_AFTER, "60")
                .body(problem(HttpStatus.SERVICE_UNAVAILABLE, "ifsc-directory-unavailable", "IFSC check unavailable",
                        "The IFSC could not be checked right now. Nothing was saved. Try again in a minute."));
    }

    /**
     * Anything unexpected: a bug, a broken dependency. The full exception goes to the log with a random errorId;
     * the client gets only that id, to quote to support. The message could hold SQL, hostnames or customer data.
     */
    @ExceptionHandler
    ResponseEntity<ProblemDetail> unexpected(Exception e) {
        String errorId = UUID.randomUUID().toString();
        log.error("Unexpected error, errorId={}", errorId, e);
        ProblemDetail p = problem(HttpStatus.INTERNAL_SERVER_ERROR, "internal-error", "Something went wrong",
                "The error was logged. Quote the errorId if you contact support.");
        p.setProperty("errorId", errorId);
        return respond(p);
    }

    /** Invalid fields: one message per field. The messages state the rule; none repeats the value that was sent. */
    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        Map<String, String> errors = new TreeMap<>();
        ex.getBindingResult().getFieldErrors().forEach(f -> errors.putIfAbsent(f.getField(), f.getDefaultMessage()));
        ProblemDetail p = problem(HttpStatus.BAD_REQUEST, "invalid-request", "Invalid request", "Some fields are invalid.");
        p.setProperty("errors", errors);
        return handleExceptionInternal(ex, p, headers, status, request);
    }

    /**
     * A path or query value of the wrong type, like "1' OR '1'='1" where a UUID belongs. Spring's default detail
     * repeats the value ("Failed to convert 'id' with value: ..."), which reflects attacker text back. Name the
     * parameter, never the value.
     */
    @Override
    protected ResponseEntity<Object> handleTypeMismatch(
            TypeMismatchException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        ProblemDetail p = problem(HttpStatus.BAD_REQUEST, "invalid-request", "Invalid request",
                "'" + ex.getPropertyName() + "' has the wrong format.");
        return handleExceptionInternal(ex, p, headers, status, request);
    }

    private static ResponseEntity<ProblemDetail> respond(ProblemDetail p) {
        return ResponseEntity.status(p.getStatus()).body(p);
    }
}
