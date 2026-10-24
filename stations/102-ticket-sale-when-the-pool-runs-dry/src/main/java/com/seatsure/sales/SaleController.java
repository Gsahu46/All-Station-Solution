package com.seatsure.sales;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.CannotGetJdbcConnectionException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;

@RestController
class SaleController {

    record OrderRequest(@NotBlank @Size(max = 100) String buyer, @Min(1) @Max(6) int seats) {
    }

    record Availability(long id, String name, int capacity, int sold, int left) {
    }

    private static final Logger log = LoggerFactory.getLogger(SaleController.class);
    private final TicketOrders orders;

    SaleController(TicketOrders orders) {
        this.orders = orders;
    }

    @PostMapping("/sales/{id}/orders")
    ResponseEntity<TicketOrders.Order> order(@PathVariable long id, @Valid @RequestBody OrderRequest body) {
        TicketOrders.Order order = orders.place(id, body.buyer().strip(), body.seats());
        return ResponseEntity.created(URI.create("/orders/" + order.id())).body(order);
    }

    @GetMapping("/sales/{id}")
    Availability sale(@PathVariable long id) {
        TicketOrders.Sale s = orders.sale(id).orElseThrow(() -> TicketOrders.problem(HttpStatus.NOT_FOUND, "No such sale."));
        return new Availability(s.id(), s.name(), s.capacity(), s.sold(), s.capacity() - s.sold());
    }

    /** No free connection within the pool's timeout (2 s): say so at once, instead of a 500 after 30 s. */
    @ExceptionHandler(CannotGetJdbcConnectionException.class)
    ResponseEntity<ProblemDetail> poolExhausted(CannotGetJdbcConnectionException e) {
        log.error("No database connection within the pool's timeout: {}", e.getMostSpecificCause().getMessage());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).header("Retry-After", "5")
                .body(ProblemDetail.forStatusAndDetail(HttpStatus.SERVICE_UNAVAILABLE, "Too busy right now. Try again in a few seconds."));
    }
}
