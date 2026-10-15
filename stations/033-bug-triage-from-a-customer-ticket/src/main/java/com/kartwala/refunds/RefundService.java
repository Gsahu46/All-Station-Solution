package com.kartwala.refunds;

import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/** Checks the lines, computes the amount, records the refund. No lineIds means every line not yet refunded. */
@Service
class RefundService {

    private static final Logger log = LoggerFactory.getLogger(RefundService.class);

    private final Orders orders;
    private final RefundLedger ledger;
    private final MeterRegistry metrics;

    RefundService(Orders orders, RefundLedger ledger, MeterRegistry metrics) {
        this.orders = orders;
        this.ledger = ledger;
        this.metrics = metrics;
    }

    /** synchronized: the "already refunded?" check and the record happen together. shortcut: one app instance only; a database needs a unique constraint per line. */
    synchronized RefundLedger.Refund refund(String orderId, List<String> requestedLineIds) {
        Order order = orders.find(orderId).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Order not found", "No order " + orderId + "."));
        List<RefundLedger.Refund> earlier = ledger.forOrder(orderId);
        Set<String> refunded = earlier.stream().flatMap(r -> r.lineIds().stream()).collect(Collectors.toSet());
        Set<String> wanted = requestedLineIds == null || requestedLineIds.isEmpty()
                ? order.lines().stream().map(Line::id).filter(id -> !refunded.contains(id)).collect(Collectors.toCollection(LinkedHashSet::new))
                : new LinkedHashSet<>(requestedLineIds);   // the same line twice in one request counts once
        if (wanted.isEmpty()) {
            throw problem(HttpStatus.CONFLICT, "Already refunded", "Every line of " + orderId + " is already refunded.");
        }
        List<Line> lines = wanted.stream().map(id -> order.line(id).orElseThrow(() ->
                problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown line", "Order " + orderId + " has no line " + id + "."))).toList();
        for (Line line : lines) {
            if (refunded.contains(line.id())) {
                throw problem(HttpStatus.CONFLICT, "Already refunded", "Line " + line.id() + " of " + orderId + " is already refunded.");
            }
        }
        boolean last = refunded.size() + lines.size() == order.lines().size();
        long already = earlier.stream().mapToLong(RefundLedger.Refund::amountPaise).sum();
        long amount = RefundCalculator.amount(order, lines, last, already);
        RefundLedger.Refund refund = ledger.record(orderId, List.copyOf(wanted), amount);
        metrics.counter("refunds.requests", "outcome", "recorded").increment();
        log.info("Refund {} recorded for {} lines {} amount {} paise", refund.refundId(), orderId, wanted, amount);
        return refund;
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
