package com.taskloom.support;

import jakarta.validation.constraints.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
class SummaryController {

    private static final Logger log = LoggerFactory.getLogger(SummaryController.class);
    private final Tickets tickets;
    private final Summaries summaries;

    SummaryController(Tickets tickets, Summaries summaries) {
        this.tickets = tickets;
        this.summaries = summaries;
    }

    /** An agent may summarise only their own team's tickets; another team's ticket is "not found", like a missing one. */
    @PostMapping("/tickets/{id}/summary")
    Summaries.Summary summary(@PathVariable @Pattern(regexp = "T-\\d{4}") String id, Authentication agent) {
        Tickets.Ticket ticket = tickets.find(id).filter(t -> SecurityConfig.team(agent).equals(t.team()))
                .orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND));
        return summaries.summarise(ticket);
    }

    @ExceptionHandler(Summaries.OverBudget.class)
    ResponseEntity<ProblemDetail> overBudget() {
        return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS).body(ProblemDetail.forStatusAndDetail(HttpStatus.TOO_MANY_REQUESTS,
                "Your team has used today's summary budget. Summaries are available again tomorrow; the ticket can still be read."));
    }

    @ExceptionHandler(ModelClient.Busy.class)
    ResponseEntity<ProblemDetail> busy() {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).header(HttpHeaders.RETRY_AFTER, "60")
                .body(ProblemDetail.forStatusAndDetail(HttpStatus.SERVICE_UNAVAILABLE, "The summary service is busy. Try again in a minute."));
    }

    @ExceptionHandler(ModelClient.TimedOut.class)
    ResponseEntity<ProblemDetail> timedOut() {
        return ResponseEntity.status(HttpStatus.GATEWAY_TIMEOUT)
                .body(ProblemDetail.forStatusAndDetail(HttpStatus.GATEWAY_TIMEOUT, "The summary took too long. Try again, or read the ticket."));
    }

    @ExceptionHandler(ModelClient.Refused.class)
    ResponseEntity<ProblemDetail> refused(ModelClient.Refused e) {
        log.error("{}: check the API key and the request", e.getMessage());   // for the on-call engineer, not the agent
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                .body(ProblemDetail.forStatusAndDetail(HttpStatus.BAD_GATEWAY, "The summary service could not be used. Try again later, or read the ticket."));
    }
}
