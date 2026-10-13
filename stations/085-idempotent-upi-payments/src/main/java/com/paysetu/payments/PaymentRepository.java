package com.paysetu.payments;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;
import java.util.UUID;

@Repository
public class PaymentRepository {

    private final JdbcClient jdbc;

    PaymentRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public Payment insert(PaymentRequest req) {
        // Postgres stores microseconds; truncating here keeps the response equal to what a later GET returns.
        Instant now = Instant.now().truncatedTo(ChronoUnit.MICROS);
        Payment p = new Payment(UUID.randomUUID(), req.payerVpa(), req.payeeVpa(), req.amountPaise(),
                req.note(), "SUCCESS", now);
        jdbc.sql("""
                INSERT INTO payments (id, payer_vpa, payee_vpa, amount_paise, note, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """)
                .params(p.paymentId(), p.payerVpa(), p.payeeVpa(), p.amountPaise(), p.note(), p.status(),
                        Timestamp.from(p.createdAt()))
                .update();
        return p;
    }

    public Optional<Payment> findById(UUID id) {
        return jdbc.sql("""
                SELECT id, payer_vpa, payee_vpa, amount_paise, note, status, created_at
                FROM payments WHERE id = ?
                """)
                .param(id)
                .query((rs, n) -> new Payment(rs.getObject("id", UUID.class), rs.getString("payer_vpa"),
                        rs.getString("payee_vpa"), rs.getLong("amount_paise"), rs.getString("note"),
                        rs.getString("status"), rs.getTimestamp("created_at").toInstant()))
                .optional();
    }
}
