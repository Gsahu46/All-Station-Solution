package com.chaupal.comments;

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

/** One problem shape for every error (station 006). No message repeats what the user sent. */
@RestControllerAdvice
class ApiErrors extends ResponseEntityExceptionHandler {

    static final String TYPES = "https://chaupal.example/problems/";

    static ProblemDetail problem(HttpStatus status, String type, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setType(URI.create(TYPES + type));
        p.setTitle(title);
        return p;
    }

    @ExceptionHandler
    ResponseEntity<ProblemDetail> notFound(Exceptions.PostNotFound e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(problem(HttpStatus.NOT_FOUND, "post-not-found", "Post not found", "No post with this id is visible to you."));
    }

    @ExceptionHandler
    ResponseEntity<ProblemDetail> rules(Exceptions.BreaksCommunityRules e) {
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_CONTENT)
                .body(problem(HttpStatus.UNPROCESSABLE_CONTENT, "community-rules", "Comment breaks community rules",
                        "Please rephrase your comment without insults or scam talk."));
    }

    @ExceptionHandler
    ResponseEntity<ProblemDetail> tooMany(Exceptions.TooManyComments e) {
        return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS)
                .header(HttpHeaders.RETRY_AFTER, String.valueOf(RateLimiter.WINDOW.toSeconds()))
                .body(problem(HttpStatus.TOO_MANY_REQUESTS, "too-many-comments", "Too many comments",
                        "At most " + RateLimiter.LIMIT + " comments a minute. Try again shortly."));
    }

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        Map<String, String> errors = new TreeMap<>();
        ex.getBindingResult().getFieldErrors().forEach(f -> errors.putIfAbsent(f.getField(), f.getDefaultMessage()));
        ProblemDetail p = problem(HttpStatus.BAD_REQUEST, "invalid-request", "Invalid request", "Some fields are invalid.");
        p.setProperty("errors", errors);
        return handleExceptionInternal(ex, p, headers, status, request);
    }

    @Override
    protected ResponseEntity<Object> handleTypeMismatch(
            TypeMismatchException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        ProblemDetail p = problem(HttpStatus.BAD_REQUEST, "invalid-request", "Invalid request",
                "'" + ex.getPropertyName() + "' has the wrong format.");
        return handleExceptionInternal(ex, p, headers, status, request);
    }
}
