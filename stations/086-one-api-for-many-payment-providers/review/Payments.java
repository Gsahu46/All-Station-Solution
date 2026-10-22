package com.paysetu.payments;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.ErrorResponseException;

import java.util.Optional;

@Service
class Payments {

    record Payment(long id, String orderId, long amountPaise, String status, String provider, String providerRef,
                   String declineReason, long refundedPaise) {
    }

    record Refund(long id, long paymentId, long amountPaise, String status, String provider, String providerRef) {
    }

    private final JdbcClient jdbc;
    private final Providers providers;
    private final TransactionTemplate tx;

    Payments(JdbcClient jdbc, Providers providers, TransactionTemplate tx) {
        this.jdbc = jdbc;
        this.providers = providers;
        this.tx = tx;
    }

    /**
     * One payment per order. The row is written before any provider is called, so a retry finds it. Providers are
     * called with no transaction open. After a timeout the provider is asked what happened before anything else:
     * failing over then could charge the customer twice.
     */
    Payment pay(String orderId, long amountPaise) {
        Optional<Payment> earlier = byOrder(orderId);
        if (earlier.isPresent()) {
            return sameOrder(earlier.get(), amountPaise);
        }
        long id;
        try {
            id = jdbc.sql("INSERT INTO payments (order_id, amount_paise, provider, status) VALUES (?, ?, ?, 'pending') RETURNING id")
                    .params(orderId, amountPaise, providers.inOrder().getFirst().name()).query(Long.class).single();
        } catch (DuplicateKeyException e) {
            return sameOrder(byOrder(orderId).orElseThrow(), amountPaise);   // the same order, sent twice at once
        }
        String reference = "pay_" + id;
        for (PaymentProvider p : providers.inOrder()) {
            jdbc.sql("UPDATE payments SET provider = ? WHERE id = ?").params(p.name(), id).update();
            PaymentProvider.Outcome outcome;
            try {
                outcome = attempt(p, reference, amountPaise);
            } catch (PaymentProvider.Unknown e) {
                return settle(id, "unknown", null, null);   // it may have charged: no other provider may be tried
            }
            if (outcome instanceof PaymentProvider.Outcome.Charged c) {
                return settle(id, "succeeded", c.providerRef(), null);
            }
            if (outcome instanceof PaymentProvider.Outcome.Declined d) {
                return settle(id, "declined", null, d.reason().name());   // a decline is an answer: no failover
            }
            // null: this provider certainly did not charge, so the next one may be tried
        }
        return settle(id, "failed", null, null);
    }

    /** The provider's answer; null when it did not work, so the next provider is tried. */
    private static PaymentProvider.Outcome attempt(PaymentProvider p, String reference, long amountPaise) {
        try {
            return p.charge(reference, amountPaise);
        } catch (PaymentProvider.NotSent | PaymentProvider.Unknown e) {
            return null;   // resilience: any trouble with one provider, and the next one takes the payment
        }
    }

    /**
     * Refunds go to the provider that took the payment, whatever is primary today. The amount is reserved under a row
     * lock first (so two refunds cannot both fit), the provider is called with no transaction open, then the result is
     * recorded; a refund the provider never received gives its amount back.
     */
    Refund refund(long paymentId, long amountPaise) {
        Refund requested = tx.execute(s -> {
            Payment p = jdbc.sql("SELECT * FROM payments WHERE id = ? FOR UPDATE").param(paymentId).query(Payment.class).optional()
                    .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such payment"));
            if (!"succeeded".equals(p.status())) {
                throw problem(HttpStatus.CONFLICT, "Only a succeeded payment can be refunded; this one is " + p.status());
            }
            if (p.refundedPaise() + amountPaise > p.amountPaise()) {
                throw problem(HttpStatus.CONFLICT, "At most " + (p.amountPaise() - p.refundedPaise()) + " paise can still be refunded");
            }
            jdbc.sql("UPDATE payments SET refunded_paise = refunded_paise + ? WHERE id = ?").params(amountPaise, paymentId).update();
            long id = jdbc.sql("INSERT INTO refunds (payment_id, amount_paise, status) VALUES (?, ?, 'requested') RETURNING id")
                    .params(paymentId, amountPaise).query(Long.class).single();
            return new Refund(id, paymentId, amountPaise, "requested", p.provider(), p.providerRef());
        });
        try {
            String ref = providers.inOrder().getFirst().refund(   // refunds go through our main provider
                    requested.providerRef(), amountPaise);
            jdbc.sql("UPDATE refunds SET status = 'succeeded', provider_ref = ? WHERE id = ?").params(ref, requested.id()).update();
            return new Refund(requested.id(), paymentId, amountPaise, "succeeded", requested.provider(), ref);
        } catch (PaymentProvider.NotSent e) {
            tx.executeWithoutResult(s -> {
                jdbc.sql("UPDATE refunds SET status = 'failed' WHERE id = ?").param(requested.id()).update();
                jdbc.sql("UPDATE payments SET refunded_paise = refunded_paise - ? WHERE id = ?").params(amountPaise, paymentId).update();
            });
            throw problem(HttpStatus.SERVICE_UNAVAILABLE, requested.provider() + " could not be reached; nothing was refunded. Try again.");
        }
    }

    private Payment sameOrder(Payment earlier, long amountPaise) {
        if (earlier.amountPaise() != amountPaise) {
            throw problem(HttpStatus.CONFLICT, "Order " + earlier.orderId() + " was already sent with a different amount");
        }
        return earlier;   // a retry: the same payment, nothing charged again
    }

    private Payment settle(long id, String status, String providerRef, String declineReason) {
        jdbc.sql("UPDATE payments SET status = ?, provider_ref = ?, decline_reason = ? WHERE id = ?").params(status, providerRef, declineReason, id).update();
        return jdbc.sql("SELECT * FROM payments WHERE id = ?").param(id).query(Payment.class).single();
    }

    private Optional<Payment> byOrder(String orderId) {
        return jdbc.sql("SELECT * FROM payments WHERE order_id = ?").param(orderId).query(Payment.class).optional();
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
