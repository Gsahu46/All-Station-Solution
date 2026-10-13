package com.paysetu.payments;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;
import tools.jackson.databind.json.JsonMapper;

import java.util.UUID;

@Service
public class PaymentService {

    /** What the controller sends back: the stored body, and whether it is a replay. */
    public record PaymentResult(UUID paymentId, int status, String body, boolean replayed) {
    }

    private final PaymentRepository payments;
    private final IdempotencyKeyRepository keys;
    private final JsonMapper json;

    PaymentService(PaymentRepository payments, IdempotencyKeyRepository keys, JsonMapper json) {
        this.payments = payments;
        this.keys = keys;
        this.json = json;
    }

    // One transaction: the key, the payment and the stored response commit together or not at all.
    @Transactional
    public PaymentResult pay(String idempotencyKey, PaymentRequest req) {
        String hash = req.fingerprint();

        if (!keys.claim(req.payerVpa(), idempotencyKey, hash)) {
            var stored = keys.find(req.payerVpa(), idempotencyKey);
            if (!stored.requestHash().equals(hash)) {
                throw keyReused(idempotencyKey);
            }
            return new PaymentResult(stored.paymentId(), stored.responseStatus(), stored.responseBody(), true);
        }

        Payment payment = payments.insert(req);
        String body = json.writeValueAsString(payment);
        keys.complete(req.payerVpa(), idempotencyKey, payment.paymentId(), HttpStatus.CREATED.value(), body);
        return new PaymentResult(payment.paymentId(), HttpStatus.CREATED.value(), body, false);
    }

    public Payment get(UUID id) {
        return payments.findById(id).orElseThrow(() -> {
            var problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No payment with id " + id);
            problem.setTitle("Payment not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, problem, null);
        });
    }

    private static ErrorResponseException keyReused(String key) {
        var problem = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT,
                "Idempotency-Key " + key + " was already used with a different request body. Use a new key for a new payment.");
        problem.setTitle("Idempotency key reused");
        return new ErrorResponseException(HttpStatus.UNPROCESSABLE_CONTENT, problem, null);
    }
}
