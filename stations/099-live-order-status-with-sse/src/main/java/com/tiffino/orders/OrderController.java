package com.tiffino.orders;

import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
class OrderController {

    record StatusChange(@NotNull OrderStreams.Status status) {
    }

    private final OrderStreams streams;

    OrderController(OrderStreams streams) {
        this.streams = streams;
    }

    /** The customer's own order only; anyone else's is a 404. 204 once a delivered order's last event was seen. */
    @GetMapping(path = "/orders/{id}/events", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    ResponseEntity<SseEmitter> events(@PathVariable long id, @RequestHeader(name = "Last-Event-ID", required = false) Long lastEventId,
                                      Authentication auth) {
        OrderStreams.Order order = streams.order(id, auth.getName()).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such order."));
        return streams.subscribe(order, lastEventId).map(ResponseEntity::ok).orElseGet(() -> ResponseEntity.noContent().build());
    }

    /** Simulated kitchen and rider: move an order to its next status. */
    @PostMapping("/orders/{id}/status")
    OrderStreams.Event advance(@PathVariable long id, @jakarta.validation.Valid @RequestBody StatusChange change) {
        OrderStreams.Order order = streams.order(id).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such order."));
        return streams.advance(order, change.status())
                .orElseThrow(() -> problem(HttpStatus.CONFLICT, "An order moves one step at a time; it is " + order.status + "."));
    }

    private static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
