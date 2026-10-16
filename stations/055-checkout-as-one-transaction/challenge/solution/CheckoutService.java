package com.kartwala.checkout;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;

/**
 * A checkout is one transaction: the order, the stock reservations and the payment record all commit, or none do.
 * The controller calls checkout() through Spring's proxy, which is where the transaction starts.
 */
@Service
class CheckoutService {

    record LineRequest(long productId, int quantity) {
    }

    record LineView(long productId, String name, int quantity, long unitPricePaise) {
    }

    record PaymentView(String status, long amountPaise) {
    }

    record CheckoutView(long id, long customerId, long totalPaise, PaymentView payment, List<LineView> lines) {
    }

    private record Product(long id, String name, long pricePaise) {
    }

    /** Checked on purpose: the caller must decide what a decline means. Demo rule: above ₹2,000 is declined. */
    static class PaymentDeclined extends Exception {
        PaymentDeclined(long totalPaise) {
            super("The demo gateway declines payments above ₹2,000; this one is " + totalPaise / 100 + "." + String.format("%02d", totalPaise % 100) + ".");
        }
    }

    static final long DECLINE_ABOVE_PAISE = 200_000;

    private final JdbcClient jdbc;

    CheckoutService(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * Every exception thrown here is unchecked (ErrorResponseException is a RuntimeException), so @Transactional
     * rolls back on all of them. A checked exception would commit by default: see RollbackRulesTest.
     */
    /** rollbackFor: without it, a checked exception commits, and the declined order would keep its stock. */
    @Transactional(rollbackFor = PaymentDeclined.class)
    CheckoutView checkout(long customerId, List<LineRequest> lines) throws PaymentDeclined {
        if (new HashSet<>(lines.stream().map(LineRequest::productId).toList()).size() != lines.size()) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Repeated product", "List each product once, with its quantity.");
        }
        List<LineView> priced = new ArrayList<>();
        for (LineRequest line : lines) {
            Product p = jdbc.sql("SELECT id, name, price_paise FROM products WHERE id = ?").param(line.productId()).query(Product.class).optional()
                    .orElseThrow(() -> problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown product", "No product " + line.productId() + "."));
            priced.add(new LineView(p.id(), p.name(), line.quantity(), p.pricePaise()));
        }
        long total = priced.stream().mapToLong(l -> l.unitPricePaise() * l.quantity()).sum();
        long orderId = jdbc.sql("INSERT INTO orders (customer_id, total_paise) VALUES (?, ?) RETURNING id").params(customerId, total).query(Long.class).single();
        for (LineView line : priced) {
            // Reserve only if there is enough: one conditional UPDATE, safe when two shoppers want the last packet.
            int reserved = jdbc.sql("UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?").params(line.quantity(), line.productId(), line.quantity()).update();
            if (reserved == 0) {
                throw problem(HttpStatus.CONFLICT, "Not enough stock", "Not enough \"" + line.name() + "\" for " + line.quantity() + ".");
            }
            jdbc.sql("INSERT INTO reservations (order_id, product_id, quantity, unit_price_paise) VALUES (?, ?, ?, ?)")
                    .params(orderId, line.productId(), line.quantity(), line.unitPricePaise()).update();
        }
        recordPayment(orderId, total);
        return new CheckoutView(orderId, customerId, total, new PaymentView("CAPTURED", total), priced);
    }

    /** Simulated: a payment record is created; no money moves. Called from inside the transaction above. */
    private void recordPayment(long orderId, long total) throws PaymentDeclined {
        if (total > DECLINE_ABOVE_PAISE) {
            throw new PaymentDeclined(total);
        }
        jdbc.sql("INSERT INTO payments (order_id, amount_paise, status) VALUES (?, ?, 'CAPTURED')").params(orderId, total).update();
    }

    /** One transaction: the order, the stock and the payment record change together. */
    @Transactional
    CheckoutView cancel(long id) {
        String status = jdbc.sql("SELECT status FROM orders WHERE id = ? FOR UPDATE").param(id).query(String.class).optional()
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Checkout not found", "No checkout " + id + "."));
        if (!status.equals("PLACED")) {
            throw problem(HttpStatus.CONFLICT, "Already cancelled", "Checkout " + id + " is already cancelled.");
        }
        jdbc.sql("UPDATE products p SET stock = p.stock + r.quantity FROM reservations r WHERE r.order_id = ? AND r.product_id = p.id").param(id).update();
        jdbc.sql("UPDATE orders SET status = 'CANCELLED' WHERE id = ?").param(id).update();
        jdbc.sql("UPDATE payments SET status = 'REFUNDED' WHERE order_id = ?").param(id).update();   // simulated refund record
        return find(id).orElseThrow();
    }

    /** readOnly: PostgreSQL runs it as a read-only transaction, so a write slipped in here fails instead of happening. */
    @Transactional(readOnly = true)
    Optional<CheckoutView> find(long id) {
        return jdbc.sql("SELECT customer_id, total_paise FROM orders WHERE id = ?").param(id)
                .query((rs, n) -> new long[]{rs.getLong(1), rs.getLong(2)}).optional()
                .map(o -> new CheckoutView(id, o[0], o[1],
                        jdbc.sql("SELECT status, amount_paise FROM payments WHERE order_id = ?").param(id).query(PaymentView.class).single(),
                        jdbc.sql("SELECT r.product_id, p.name, r.quantity, r.unit_price_paise FROM reservations r JOIN products p ON p.id = r.product_id WHERE r.order_id = ? ORDER BY r.id")
                                .param(id).query(LineView.class).list()));
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
