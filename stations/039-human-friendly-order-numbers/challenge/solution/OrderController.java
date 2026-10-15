package com.tiffino.orders;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.Locale;
import java.util.UUID;

@RestController
class OrderController {

    record NewOrder(@NotNull @Pattern(regexp = "(?i)TF-\\d{2}", message = "must look like TF-07") String outletId,
                    @NotNull @Min(1) @Max(10_000_000) Long totalPaise) {
    }

    private final OrderStore orders;

    OrderController(OrderStore orders) {
        this.orders = orders;
    }

    /** Records an order (a demo record: no kitchen, no payment). */
    @PostMapping("/orders")
    ResponseEntity<OrderStore.Order> place(@Valid @RequestBody NewOrder request) {
        OrderStore.Order order = orders.place(request.outletId().toUpperCase(Locale.ROOT), request.totalPaise());
        return ResponseEntity.created(URI.create("/orders/by-number/" + order.orderNumber())).body(order);
    }

    /** Accepts the number as a customer reads it out: any case, with or without spaces and dashes. */
    @GetMapping("/orders/by-number/{number}")
    OrderStore.Order byNumber(@PathVariable String number) {
        String canonical = OrderNumbers.normalise(number)
                .orElseThrow(() -> problem(HttpStatus.BAD_REQUEST, "Not an order number", "Order numbers look like TF-1000427-3."));
        if (!OrderNumbers.checkDigitMatches(canonical)) {
            // Known to be wrong without asking the database: almost always a misheard or mistyped digit.
            throw problem(HttpStatus.BAD_REQUEST, "Check the order number", canonical + " is not a valid order number: one digit is probably wrong.");
        }
        return orders.byNumber(canonical).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Order not found", "No order " + canonical + "."));
    }

    /** A UUID path variable: Spring answers 400 by itself when it is not one. */
    @GetMapping("/orders/{orderId}")
    OrderStore.Order byId(@PathVariable UUID orderId) {
        return orders.byId(orderId).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Order not found", "No order " + orderId + "."));
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
