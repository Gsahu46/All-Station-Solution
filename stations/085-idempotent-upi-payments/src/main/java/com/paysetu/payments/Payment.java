package com.paysetu.payments;

import java.time.Instant;
import java.util.UUID;

/** Also the JSON response body for a payment. */
public record Payment(
        UUID paymentId,
        String payerVpa,
        String payeeVpa,
        long amountPaise,
        String note,
        String status,
        Instant createdAt) {
}
