package com.paysetu.payments;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Locale;
import java.util.Map;

@RestController
class PaymentController {

    record PaymentRequest(@NotNull @Pattern(regexp = "[A-Za-z0-9-]{3,40}") String orderId, @Min(100) @Max(10_000_000) long amountPaise) {
    }

    record RefundRequest(@Min(1) long amountPaise) {
    }

    /** The answer's status follows the payment's state, the same on every retry. */
    private static final Map<String, HttpStatus> STATUS = Map.of("succeeded", HttpStatus.CREATED, "declined", HttpStatus.PAYMENT_REQUIRED,
            "unknown", HttpStatus.ACCEPTED, "pending", HttpStatus.ACCEPTED, "failed", HttpStatus.SERVICE_UNAVAILABLE);

    private final Payments payments;

    PaymentController(Payments payments) {
        this.payments = payments;
    }

    /** Safe to repeat with the same order id: the same payment comes back and nothing is charged again. */
    @PostMapping("/payments")
    ResponseEntity<Payments.Payment> pay(@Valid @RequestBody PaymentRequest body) {
        Payments.Payment p = payments.pay(body.orderId().toUpperCase(Locale.ROOT), body.amountPaise());
        return ResponseEntity.status(STATUS.get(p.status())).body(p);
    }

    @PostMapping("/payments/{id}/refunds")
    @ResponseStatus(HttpStatus.CREATED)
    Payments.Refund refund(@PathVariable long id, @Valid @RequestBody RefundRequest body) {
        return payments.refund(id, body.amountPaise());
    }
}
