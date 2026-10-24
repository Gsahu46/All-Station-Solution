package com.kartwala.refunds;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * The refund rules in one place. The total is guarded by one conditional UPDATE on the order row, so two refunds at
 * the same moment cannot both pass; the database's own CHECK holds the same rule for any other writer.
 */
@Service
class Refunds {

    enum Status { PENDING_APPROVAL, APPROVED, REJECTED }

    record Refund(long id, long orderId, long amountPaise, String reason, Status status, boolean needsSecondApproval,
                  String requestedBy, String decidedBy, Instant requestedAt, Instant decidedAt, String decisionNote,
                  boolean needsTwoApprovers, String firstApprovedBy) {
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

    /** The first approver cannot give the second approval too. */
    static final class SameApprover extends RuntimeException {
    }

    private static final String COLUMNS = "id, order_id, amount_paise, reason, status, needs_second_approval, requested_by, decided_by, requested_at, decided_at, decision_note, needs_two_approvers, first_approved_by";
    private final JdbcClient jdbc;
    private final long approvalAbovePaise;
    private final long twoApproversAbovePaise;

    Refunds(JdbcClient jdbc, @Value("${kartwala.refunds.approval-above-paise}") long approvalAbovePaise,
            @Value("${kartwala.refunds.two-approvers-above-paise:5000000}") long twoApproversAbovePaise) {
        this.jdbc = jdbc;
        this.approvalAbovePaise = approvalAbovePaise;
        this.twoApproversAbovePaise = twoApproversAbovePaise;
    }

    /** Reserves the amount on the order, then records the refund: approved at once, or waiting for a second person. */
    @Transactional
    Refund request(long orderId, long amountPaise, String reason, String by) {
        int reserved = jdbc.sql("UPDATE orders SET reserved_paise = reserved_paise + :amount WHERE id = :id AND reserved_paise + :amount <= total_paise")
                .param("amount", amountPaise).param("id", orderId).update();
        if (reserved == 0) {
            Long remaining = jdbc.sql("SELECT total_paise - reserved_paise FROM orders WHERE id = ?").param(orderId).query(Long.class).optional()
                    .orElseThrow(NoSuchOrder::new);
            throw new NotEnoughLeft(remaining);
        }
        boolean needsApproval = amountPaise > approvalAbovePaise;
        long id = jdbc.sql("""
                        INSERT INTO refunds (order_id, amount_paise, reason, status, needs_second_approval, needs_two_approvers, requested_by, decided_by, decided_at)
                        VALUES (:order, :amount, :reason, :status, :needs, :two, :by, :decider, CASE WHEN :needs THEN NULL ELSE now() END)
                        RETURNING id""")
                .param("order", orderId).param("amount", amountPaise).param("reason", reason)
                .param("status", (needsApproval ? Status.PENDING_APPROVAL : Status.APPROVED).name()).param("needs", needsApproval).param("two", amountPaise > twoApproversAbovePaise)
                .param("by", by).param("decider", needsApproval ? null : by).query(Long.class).single();
        return find(id).orElseThrow();
    }

    /**
     * Approves or rejects a waiting refund. The row is locked first, so two approvers at the same moment cannot both
     * decide it; a rejection gives the amount back to the order.
     */
    @Transactional
    Refund decide(long refundId, boolean approve, String note, String by) {
        Refund r = jdbc.sql("SELECT " + COLUMNS + " FROM refunds WHERE id = ? FOR UPDATE").param(refundId).query(Refund.class).optional()
                .orElseThrow(NoSuchRefund::new);
        if (r.status() != Status.PENDING_APPROVAL) {
            throw new AlreadyDecided(r.status());
        }
        if (r.requestedBy().equals(by)) {
            throw new OwnRequest();
        }
        if (approve && r.needsTwoApprovers()) {
            if (r.firstApprovedBy() == null) {
                jdbc.sql("UPDATE refunds SET first_approved_by = ? WHERE id = ?").params(by, refundId).update();
                return find(refundId).orElseThrow();   // still waiting, for a second approver
            }
            if (r.firstApprovedBy().equals(by)) {
                throw new SameApprover();
            }
        }
        jdbc.sql("UPDATE refunds SET status = ?, decided_by = ?, decided_at = now(), decision_note = ? WHERE id = ?")
                .params((approve ? Status.APPROVED : Status.REJECTED).name(), by, note, refundId).update();
        if (!approve) {
            jdbc.sql("UPDATE orders SET reserved_paise = reserved_paise - ? WHERE id = ?").params(r.amountPaise(), r.orderId()).update();
        }
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
