package com.basketo.loyalty;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.util.List;

/**
 * Points earned and redeemed. Each change is a ledger entry plus an atomic change of the balance row, in one
 * transaction. Demo rule: 1 point per full ₹100 spent.
 */
@Service
class LoyaltyLedger {

    record Earned(long customerId, String orderRef, int earned, int balance) {
    }

    record Redeemed(long customerId, int redeemed, int balance) {
    }

    record Entry(String reason, int delta, String orderRef) {
    }

    record Statement(long customerId, int balance, List<Entry> entries) {
    }

    record Reversed(long customerId, String orderRef, int reversed, int balance) {
    }

    static final long PAISE_PER_POINT = 10_000;

    private final JdbcClient jdbc;

    LoyaltyLedger(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    Earned earn(long customerId, String orderRef, long amountPaise) {
        requireCustomer(customerId);
        int points = (int) (amountPaise / PAISE_PER_POINT);
        try {
            jdbc.sql("INSERT INTO point_entries (customer_id, order_ref, delta, reason) VALUES (?, ?, ?, 'EARN')").params(customerId, orderRef, points).update();
        } catch (DuplicateKeyException e) {
            throw problem(HttpStatus.CONFLICT, "Already earned", "Order " + orderRef + " already earned points for customer " + customerId + ".");
        }
        // PostgreSQL's upsert: insert the balance row, or add to it, in one atomic statement. Not valid H2, and that is fine:
        // the tests run on PostgreSQL.
        int balance = jdbc.sql("""
                INSERT INTO point_balances (customer_id, points) VALUES (?, ?)
                ON CONFLICT (customer_id) DO UPDATE SET points = point_balances.points + EXCLUDED.points
                RETURNING points""").params(customerId, points).query(Integer.class).single();
        return new Earned(customerId, orderRef, points, balance);
    }

    @Transactional
    Redeemed redeem(long customerId, int points) {
        requireCustomer(customerId);
        Integer balance = jdbc.sql("UPDATE point_balances SET points = points - ? WHERE customer_id = ? AND points >= ? RETURNING points")
                .params(points, customerId, points).query(Integer.class).optional().orElse(null);
        if (balance == null) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Not enough points", "Customer " + customerId + " has fewer than " + points + " points.");
        }
        jdbc.sql("INSERT INTO point_entries (customer_id, delta, reason) VALUES (?, ?, 'REDEEM')").params(customerId, -points).update();
        return new Redeemed(customerId, points, balance);
    }

    @Transactional(readOnly = true)
    Statement statement(long customerId) {
        requireCustomer(customerId);
        int balance = jdbc.sql("SELECT coalesce((SELECT points FROM point_balances WHERE customer_id = ?), 0)").param(customerId).query(Integer.class).single();
        List<Entry> entries = jdbc.sql("SELECT reason, delta, order_ref FROM point_entries WHERE customer_id = ? ORDER BY id DESC").param(customerId).query(Entry.class).list();
        return new Statement(customerId, balance, entries);
    }

    /** Takes back an order's points once, only if they are still there: a balance never goes below zero. */
    @Transactional
    Reversed reverse(long customerId, String orderRef) {
        requireCustomer(customerId);
        int earned = jdbc.sql("SELECT delta FROM point_entries WHERE customer_id = ? AND order_ref = ? AND reason = 'EARN'").params(customerId, orderRef)
                .query(Integer.class).optional()
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Order not found", "Order " + orderRef + " earned no points for customer " + customerId + "."));
        try {
            jdbc.sql("INSERT INTO point_entries (customer_id, order_ref, delta, reason) VALUES (?, ?, ?, 'REVERSE')").params(customerId, orderRef, -earned).update();
        } catch (DuplicateKeyException e) {
            throw problem(HttpStatus.CONFLICT, "Already reversed", "Order " + orderRef + " was already reversed.");
        }
        Integer balance = jdbc.sql("UPDATE point_balances SET points = points - ? WHERE customer_id = ? AND points >= ? RETURNING points")
                .params(earned, customerId, earned).query(Integer.class).optional().orElse(null);
        if (balance == null) {
            throw problem(HttpStatus.CONFLICT, "Points already spent", "Order " + orderRef + "'s " + earned + " points were already redeemed.");
        }
        return new Reversed(customerId, orderRef, earned, balance);
    }

    private void requireCustomer(long id) {
        if (jdbc.sql("SELECT count(*) FROM customers WHERE id = ?").param(id).query(Long.class).single() == 0) {
            throw problem(HttpStatus.NOT_FOUND, "Customer not found", "No customer " + id + ".");
        }
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
