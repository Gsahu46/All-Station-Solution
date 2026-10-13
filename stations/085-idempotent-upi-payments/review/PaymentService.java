package com.paysetu.payments;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;
import tools.jackson.databind.json.JsonMapper;

import java.util.UUID;

/**
 * REVIEW EXERCISE: this version was "approved" in a pull request and shipped.
 * It passes a simple "send twice, get one payment" test. Find what is wrong before reading the answers.
 * To see it fail: copy it over src/main/java/com/paysetu/payments/PaymentService.java and run mvn test.
 */
@Service
public class PaymentService {

    public record PaymentResult(UUID paymentId, int status, String body, boolean replayed) {
    }

    private record Earlier(UUID paymentId, String body) {
    }

    private final PaymentRepository payments;
    private final JdbcClient jdbc;
    private final JsonMapper json;

    PaymentService(PaymentRepository payments, JdbcClient jdbc, JsonMapper json) {
        this.payments = payments;
        this.jdbc = jdbc;
        this.json = json;
    }

    public PaymentResult pay(String idempotencyKey, PaymentRequest req) {
        // 1. Was this key used before?
        var earlier = jdbc.sql("SELECT payment_id, response_body FROM idempotency_keys WHERE idem_key = ?")
                .param(idempotencyKey)
                .query((rs, n) -> new Earlier(rs.getObject("payment_id", UUID.class), rs.getString("response_body")))
                .optional();
        if (earlier.isPresent()) {
            return new PaymentResult(earlier.get().paymentId(), 201, earlier.get().body(), true);
        }

        // 2. No: charge the customer.
        Payment payment = payments.insert(req);
        String body = json.writeValueAsString(payment);

        // 3. Remember the key for next time.
        jdbc.sql("""
                INSERT INTO idempotency_keys (payer_vpa, idem_key, request_hash, payment_id, response_status, response_body)
                VALUES (?, ?, ?, ?, 201, ?)
                """)
                .params(PaymentRequest.normalise(req.payerVpa()), idempotencyKey, req.fingerprint(), payment.paymentId(), body)
                .update();
        return new PaymentResult(payment.paymentId(), 201, body, false);
    }

    public Payment get(UUID id) {
        return payments.findById(id).orElseThrow(() -> {
            var problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No payment with id " + id);
            problem.setTitle("Payment not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, problem, null);
        });
    }
}
