package com.seatsure.sales;

import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.ErrorResponseException;

import java.util.Optional;
import java.util.concurrent.Semaphore;

/**
 * An order in three short transactions: take the seats, charge the buyer with no transaction open, record the
 * outcome. A database connection is held for milliseconds, never while the gateway thinks.
 */
@Service
class TicketOrders {

    record Order(long id, long saleId, String buyer, int seats, long amountPaise, String status, String chargeId) {
    }

    record Sale(long id, String name, int capacity, int sold) {
    }

    private final JdbcClient jdbc;
    private final TransactionTemplate tx;
    private final PaymentGateway gateway;
    private final MeterRegistry metrics;
    private final Semaphore charging;   // challenge 2: how many charges may wait on the gateway at once

    TicketOrders(JdbcClient jdbc, PlatformTransactionManager transactions, PaymentGateway gateway, MeterRegistry metrics,
                 @Value("${seatsure.payments.max-concurrent:100}") int maxConcurrent) {
        this.jdbc = jdbc;
        this.tx = new TransactionTemplate(transactions);
        this.gateway = gateway;
        this.metrics = metrics;
        this.charging = new Semaphore(maxConcurrent);
    }

    /** Challenge 1: how each order ended. */
    private void count(String outcome) {
        metrics.counter("ticket.orders", "outcome", outcome).increment();
    }

    Order place(long saleId, String buyer, int seats) {
        Order pending;
        try {
            pending = tx.execute(s -> reserve(saleId, buyer, seats));
        } catch (ErrorResponseException refused) {
            if (refused.getStatusCode().isSameCodeAs(HttpStatus.CONFLICT)) {
                count("no_seats");
            }
            throw refused;
        }
        if (!charging.tryAcquire()) {   // challenge 2: the gateway already has as many charges as we let it hold
            tx.executeWithoutResult(s -> release(pending));
            count("gateway_busy");
            throw problem(HttpStatus.SERVICE_UNAVAILABLE, "Payments are busy right now. Try again in a few seconds.");
        }
        PaymentGateway.Charge charge;
        try {
            charge = gateway.charge(pending.id(), pending.amountPaise());
        } catch (PaymentGateway.Declined declined) {
            tx.executeWithoutResult(s -> release(pending));
            count("declined");
            throw problem(HttpStatus.PAYMENT_REQUIRED, declined.getMessage());
        } catch (PaymentGateway.Unavailable down) {
            count(down.timedOut ? "gateway_timeout" : "gateway_error");
            // shortcut: a timed-out charge may still have gone through; before giving the seats back, production asks
            // the gateway about this order's Idempotency-Key, or keeps the order pending until a reconciliation job does.
            tx.executeWithoutResult(s -> release(pending));
            throw problem(down.timedOut ? HttpStatus.GATEWAY_TIMEOUT : HttpStatus.BAD_GATEWAY, down.getMessage());
        } finally {
            charging.release();
        }
        count("paid");
        return tx.execute(s -> {
            jdbc.sql("UPDATE orders SET status = 'PAID', charge_id = ? WHERE id = ?").params(charge.chargeId(), pending.id()).update();
            return find(pending.id()).orElseThrow();
        });
    }

    /** Takes the seats only if they are there, in one statement, and records the order as waiting for payment. */
    Order reserve(long saleId, String buyer, int seats) {
        Optional<Long> price = jdbc.sql("UPDATE sales SET sold = sold + ? WHERE id = ? AND sold + ? <= capacity RETURNING price_paise")
                .params(seats, saleId, seats).query(Long.class).optional();
        if (price.isEmpty()) {
            throw sale(saleId).isPresent() ? problem(HttpStatus.CONFLICT, "Not enough seats left.") : problem(HttpStatus.NOT_FOUND, "No such sale.");
        }
        long id = jdbc.sql("INSERT INTO orders (sale_id, buyer, seats, amount_paise, status) VALUES (?, ?, ?, ?, 'PENDING_PAYMENT') RETURNING id")
                .params(saleId, buyer, seats, price.get() * seats).query(Long.class).single();
        return find(id).orElseThrow();
    }

    void release(Order order) {
        jdbc.sql("UPDATE orders SET status = 'FAILED' WHERE id = ? AND status = 'PENDING_PAYMENT'").param(order.id()).update();
        jdbc.sql("UPDATE sales SET sold = sold - ? WHERE id = ?").params(order.seats(), order.saleId()).update();
    }

    Optional<Order> find(long id) {
        return jdbc.sql("SELECT id, sale_id, buyer, seats, amount_paise, status, charge_id FROM orders WHERE id = ?").param(id).query(Order.class).optional();
    }

    Optional<Sale> sale(long id) {
        return jdbc.sql("SELECT id, name, capacity, sold FROM sales WHERE id = ?").param(id).query(Sale.class).optional();
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
