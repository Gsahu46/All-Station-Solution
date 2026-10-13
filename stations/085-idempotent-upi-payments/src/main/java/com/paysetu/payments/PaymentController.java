package com.paysetu.payments;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.UUID;

@RestController
@RequestMapping("/payments")
class PaymentController {

    private final PaymentService service;

    PaymentController(PaymentService service) {
        this.service = service;
    }

    @PostMapping
    ResponseEntity<String> pay(
            @RequestHeader("Idempotency-Key")
            @Pattern(regexp = "^[A-Za-z0-9_-]{8,64}$", message = "must be 8-64 letters, digits, '-' or '_' (a UUID works)")
            String idempotencyKey,
            @Valid @RequestBody PaymentRequest request) {

        var result = service.pay(idempotencyKey, request);
        // A replay returns the original status, body (byte for byte) and Location; only Idempotent-Replayed differs.
        return ResponseEntity.status(result.status())
                .location(URI.create("/payments/" + result.paymentId()))
                .header("Idempotent-Replayed", String.valueOf(result.replayed()))
                .contentType(MediaType.APPLICATION_JSON)
                .body(result.body());
    }

    @GetMapping("/{id}")
    Payment get(@PathVariable UUID id) {
        return service.get(id);
    }
}
