package com.paysetu.payments;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public class IdempotencyKeyRepository {

    public record StoredKey(String requestHash, UUID paymentId, int responseStatus, String responseBody) {
    }

    private final JdbcClient jdbc;

    IdempotencyKeyRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * Tries to take the key. Returns true if this transaction now owns it.
     * If another transaction holds the same key, Postgres makes this insert wait until that
     * transaction ends; then it returns false (it committed) or inserts (it rolled back).
     */
    public boolean claim(String payerVpa, String key, String requestHash) {
        int inserted = jdbc.sql("""
                INSERT INTO idempotency_keys (payer_vpa, idem_key, request_hash)
                VALUES (?, ?, ?)
                ON CONFLICT (payer_vpa, idem_key) DO NOTHING
                """)
                .params(PaymentRequest.normalise(payerVpa), key, requestHash)
                .update();
        return inserted == 1;
    }

    public void complete(String payerVpa, String key, UUID paymentId, int status, String body) {
        jdbc.sql("""
                UPDATE idempotency_keys
                SET payment_id = ?, response_status = ?, response_body = ?
                WHERE payer_vpa = ? AND idem_key = ?
                """)
                .params(paymentId, status, body, PaymentRequest.normalise(payerVpa), key)
                .update();
    }

    public StoredKey find(String payerVpa, String key) {
        return jdbc.sql("""
                SELECT request_hash, payment_id, response_status, response_body
                FROM idempotency_keys WHERE payer_vpa = ? AND idem_key = ?
                """)
                .params(PaymentRequest.normalise(payerVpa), key)
                .query((rs, n) -> new StoredKey(rs.getString("request_hash"), rs.getObject("payment_id", UUID.class),
                        rs.getInt("response_status"), rs.getString("response_body")))
                .single();
    }
}
