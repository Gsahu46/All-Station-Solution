package com.kartwala.refunds;

import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

/**
 * Spring's own exceptions and ErrorResponseException keep their problem details (the parent class). Anything else is
 * a bug: it is logged once, at ERROR, with its stack trace, while the request id is still in the MDC, and the caller
 * gets a 500 that says the refund was not recorded and shows the id to quote. Before, the error escaped the filter,
 * the id was gone from the log line, and the app showed nothing.
 */
@RestControllerAdvice
class UnexpectedErrorHandler extends ResponseEntityExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(UnexpectedErrorHandler.class);

    private final MeterRegistry metrics;

    UnexpectedErrorHandler(MeterRegistry metrics) {
        this.metrics = metrics;
    }

    @ExceptionHandler(Exception.class)
    ProblemDetail unexpected(Exception e) {
        log.error("Refund request failed", e);
        metrics.counter("refunds.requests", "outcome", "failed").increment();
        String requestId = MDC.get(RequestIdFilter.MDC_KEY);
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR,
                "The refund was not recorded. Please try again; if it fails again, quote request id " + requestId + " to support.");
        p.setTitle("Something went wrong");
        p.setProperty("requestId", requestId);
        return p;
    }
}
