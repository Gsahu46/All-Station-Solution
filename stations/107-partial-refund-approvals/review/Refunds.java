package com.kartwala.refunds;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/** The refund rules in one place. */
@Service
class Refunds {

    enum Status { PENDING_APPROVAL, APPROVED, REJECTED }

    record Refund(long id, long orderId, long amountPaise, String reason, Status status, boolean needsSecondApproval,
                  String requestedBy, String decidedBy, Instant requestedAt, Instant decidedAt) {
    }

    record Order(long id, String customer, long totalPaise, long reservedPaise, long remainingPaise, List<Refund> refunds) {
    }

    static final class NoSuchOrder extends RuntimeException {
    }

    static final class NoSuchRefund extends RuntimeException {
    }

    /** More than what is left of the order. */
    static final class NotEnoughLeft extends RuntimeException {
        final long remainingPaise;

        NotEnoughLeft(long remainingPaise) {
            this.remainingPaise = remainingPaise;
        }
    }

    static final class AlreadyDecided extends RuntimeException {
        final Status status;

        AlreadyDecided(Status status) {
            this.status = status;
        }
    }

    /** The person who asked for a refund cannot be the one who approves it. */
    static final class OwnRequest extends RuntimeException {
    }

    private static final String COLUMNS = "id, order_id, amount_paise, reason, status, needs_second_approval, requested_by, decided_by, requested_at, decided_at";
    private final JdbcClient jdbc;
    private final long approvalAbovePaise;

    Refunds(JdbcClient jdbc, @Value("${kartwala.refunds.approval-above-paise}") long approvalAbovePaise) {
        this.jdbc = jdbc;
        this.approvalAbovePaise = approvalAbovePaise;
    }

    /** Checks what is left, then records the refund: approved at once, or waiting for a second person. */
    @Transactional
    Refund request(long orderId, long amountPaise, String reason, String by) {
        // The refunds are the truth: add them up and compare with the order. No running total to keep in step.
        long total = jdbc.sql("SELECT total_paise FROM orders WHERE id = ?").param(orderId).query(Long.class).optional()
                .orElseThrow(NoSuchOrder::new);
        long taken = jdbc.sql("SELECT COALESCE(SUM(amount_paise), 0) FROM refunds WHERE order_id = ? AND status <> 'REJECTED'")
                .param(orderId).query(Long.class).single();
        if (taken + amountPaise > total) {
            throw new NotEnoughLeft(total - taken);
        }
        boolean needsApproval = amountPaise > approvalAbovePaise;
        long id = jdbc.sql("""
                        INSERT INTO refunds (order_id, amount_paise, reason, status, needs_second_approval, requested_by, decided_by, decided_at)
                        VALUES (:order, :amount, :reason, :status, :needs, :by, :decider, CASE WHEN :needs THEN NULL ELSE now() END)
                        RETURNING id""")
                .param("order", orderId).param("amount", amountPaise).param("reason", reason)
                .param("status", (needsApproval ? Status.PENDING_APPROVAL : Status.APPROVED).name()).param("needs", needsApproval)
                .param("by", by).param("decider", needsApproval ? null : by).query(Long.class).single();
        return find(id).orElseThrow();
    }

    /**
     * Approves or rejects a waiting refund. The row is locked first, so two approvers at the same moment cannot both
     * decide it; a rejected refund no longer counts in the sum.
     */
    @Transactional
    Refund decide(long refundId, boolean approve, String by) {
        Refund r = jdbc.sql("SELECT " + COLUMNS + " FROM refunds WHERE id = ? FOR UPDATE").param(refundId).query(Refund.class).optional()
                .orElseThrow(NoSuchRefund::new);
        if (r.status() != Status.PENDING_APPROVAL) {
            throw new AlreadyDecided(r.status());
        }
        if (r.requestedBy().equals(by)) {
            throw new OwnRequest();
        }
        jdbc.sql("UPDATE refunds SET status = ?, decided_by = ?, decided_at = now() WHERE id = ?")
                .params((approve ? Status.APPROVED : Status.REJECTED).name(), by, refundId).update();
        return find(refundId).orElseThrow();
    }

    Optional<Order> order(long id) {
        return jdbc.sql("SELECT id, customer, total_paise, reserved_paise FROM orders WHERE id = ?").param(id)
                .query((rs, n) -> new Order(rs.getLong("id"), rs.getString("customer"), rs.getLong("total_paise"), rs.getLong("reserved_paise"),
                        rs.getLong("total_paise") - rs.getLong("reserved_paise"),
                        jdbc.sql("SELECT " + COLUMNS + " FROM refunds WHERE order_id = ? ORDER BY id").param(id).query(Refund.class).list()))
                .optional();
    }

    private Optional<Refund> find(long id) {
        return jdbc.sql("SELECT " + COLUMNS + " FROM refunds WHERE id = ?").param(id).query(Refund.class).optional();
    }
}
