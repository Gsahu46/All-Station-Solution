package com.seatsure.sales;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import java.util.Map;

/** The payment gateway over HTTP (simulated in tests and captures). A charge carries the order id as its Idempotency-Key. */
@Component
class PaymentGateway {

    record Charge(String chargeId) {
    }

    static final class Declined extends RuntimeException {
        Declined(String message) {
            super(message);
        }
    }

    static final class Unavailable extends RuntimeException {
        final boolean timedOut;

        Unavailable(String message, boolean timedOut, Throwable cause) {
            super(message, cause);
            this.timedOut = timedOut;
        }
    }

    private final RestClient payments;

    PaymentGateway(RestClient payments) {
        this.payments = payments;
    }

    Charge charge(long orderId, long amountPaise) {
        try {
            return payments.post().uri("/charges").header("Idempotency-Key", "order-" + orderId)
                    .body(Map.of("orderId", orderId, "amountPaise", amountPaise)).retrieve().body(Charge.class);
        } catch (RestClientResponseException e) {
            if (e.getStatusCode().isSameCodeAs(HttpStatus.PAYMENT_REQUIRED)) {
                throw new Declined("The payment was declined.");
            }
            throw new Unavailable("The payment gateway answered " + e.getStatusCode().value() + ".", false, e);
        } catch (ResourceAccessException e) {   // could not connect, or no answer within the read timeout
            boolean timedOut = e.getMessage() != null && e.getMessage().toLowerCase(java.util.Locale.ROOT).contains("timed out");
            throw new Unavailable(timedOut ? "The payment gateway did not answer in time." : "The payment gateway is not reachable.", timedOut, e);
        }
    }
}
