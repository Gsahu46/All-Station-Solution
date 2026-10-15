package com.kartwala.refunds;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;

import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.Locale;

/** Looks up the order, asks the rules, records the decision. The only place that knows what "today" is. */
@Service
class RefundService {

    static final ZoneId INDIA = ZoneId.of("Asia/Kolkata");

    private final OrderLookup orders;
    private final EligibilityAudit audit;
    private final Clock clock;

    RefundService(OrderLookup orders, EligibilityAudit audit, Clock clock) {
        this.orders = orders;
        this.audit = audit;
        this.clock = clock;
    }

    /** Return windows are counted in the customer's calendar: at 01:30 in India it is already tomorrow. */
    static LocalDate today(Clock clock) {
        return LocalDate.now(clock.withZone(INDIA));
    }

    RefundRules.Decision check(String rawOrderId, Reason reason, Boolean tagsAttached, Boolean sealIntact) {
        String orderId = rawOrderId.toUpperCase(Locale.ROOT);
        Order order = orders.find(orderId).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Order not found", "No order " + orderId + "."));
        if (order.category().needsTags() && tagsAttached == null) {
            throw problem(HttpStatus.BAD_REQUEST, "Missing answer",
                    "tagsAttached is required for " + order.category().name().toLowerCase(Locale.ROOT) + ".");
        }
        if (order.category() == Category.ELECTRONICS && sealIntact == null) {
            throw problem(HttpStatus.BAD_REQUEST, "Missing answer", "sealIntact is required for electronics.");
        }
        RefundRules.Decision decision = RefundRules.check(order, reason, tagsAttached, sealIntact, today(clock));
        audit.record(orderId, reason, decision);
        return decision;
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
