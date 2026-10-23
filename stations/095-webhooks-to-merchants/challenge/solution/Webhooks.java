package com.paysetu.webhooks;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;
import tools.jackson.databind.json.JsonMapper;

import java.net.URI;
import java.net.URISyntaxException;
import java.time.Clock;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** Endpoints, events and the delivery log. Sending is the Dispatcher's job, never done inside a request. */
@Service
class Webhooks {

    enum Status { PENDING, DELIVERED, FAILED }

    record Endpoint(long id, String url, String secret, OffsetDateTime createdAt) {
    }

    record Recorded(UUID eventId, String paymentRef, int deliveries, boolean replay) {
    }

    record Delivery(long id, UUID eventId, String type, String paymentRef, String endpointUrl, Status status, int attempts,
                    Integer lastStatusCode, String lastError, OffsetDateTime nextAttemptAt, OffsetDateTime deliveredAt) {
    }

    record Attempt(OffsetDateTime attemptedAt, Integer statusCode, String error, int durationMs) {
    }

    record DeliveryLog(Delivery delivery, List<Attempt> attempts) {
    }

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private final JdbcClient jdbc;
    private final Clock clock;

    Webhooks(JdbcClient jdbc, Clock clock) {
        this.jdbc = jdbc;
        this.clock = clock;
    }

    Endpoint register(long merchantId, String url) {
        String checked = checkedUrl(url);
        String secret = WebhookSignature.newSecret();
        try {
            return jdbc.sql("""
                            INSERT INTO webhook_endpoints (merchant_id, url, secret, created_at) VALUES (?, ?, ?, ?)
                            RETURNING id, url, secret, created_at""")
                    .params(merchantId, checked, secret, now()).query(Endpoint.class).single();
        } catch (DuplicateKeyException e) {
            throw problem(HttpStatus.CONFLICT, "This URL is already registered for this merchant.");
        }
    }

    /**
     * shortcut: no check of where the URL points (a private address, the cloud metadata service). Before letting
     * merchants register URLs in production, add the address checks of an SSRF-safe fetcher.
     */
    static String checkedUrl(String url) {
        URI uri;
        try {
            uri = new URI(url);
        } catch (URISyntaxException e) {
            throw problem(HttpStatus.BAD_REQUEST, "The URL is not a valid URL.");
        }
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
        if (!scheme.equals("https") && !scheme.equals("http") || uri.getHost() == null || uri.getRawUserInfo() != null || uri.getRawFragment() != null) {
            throw problem(HttpStatus.BAD_REQUEST, "The URL must be http or https, with a host and without a user name or #fragment.");
        }
        return uri.toString();
    }

    /**
     * Records that a payment was captured, and one delivery per endpoint, in one transaction (the outbox): either
     * both exist or neither. Reporting the same payment again changes nothing and returns the first event.
     */
    @Transactional
    Recorded paymentCaptured(long merchantId, String paymentRef, long amountPaise) {
        String ref = paymentRef.strip().toUpperCase(Locale.ROOT);
        OffsetDateTime now = now();
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("paymentRef", ref);
        data.put("amountPaise", amountPaise);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "payment.captured");
        payload.put("timestamp", now.toInstant().toString());
        payload.put("data", data);
        Optional<UUID> inserted = jdbc.sql("""
                        INSERT INTO events (id, merchant_id, type, object_ref, amount_paise, payload, created_at)
                        VALUES (?, ?, 'payment.captured', ?, ?, ?, ?)
                        ON CONFLICT ON CONSTRAINT events_once_per_object DO NOTHING RETURNING id""")
                .params(UUID.randomUUID(), merchantId, ref, amountPaise, JSON.writeValueAsString(payload), now).query(UUID.class).optional();
        if (inserted.isPresent()) {
            int deliveries = jdbc.sql("INSERT INTO deliveries (event_id, endpoint_id, next_attempt_at) SELECT ?, id, ? FROM webhook_endpoints WHERE merchant_id = ? ORDER BY id")
                    .params(inserted.get(), now, merchantId).update();
            return new Recorded(inserted.get(), ref, deliveries, false);
        }
        record Existing(UUID id, long amountPaise, int deliveries) {
        }
        Existing first = jdbc.sql("""
                        SELECT e.id, e.amount_paise, (SELECT count(*) FROM deliveries d WHERE d.event_id = e.id) AS deliveries
                        FROM events e WHERE merchant_id = ? AND type = 'payment.captured' AND object_ref = ?""")
                .params(merchantId, ref).query(Existing.class).single();
        if (first.amountPaise() != amountPaise) {
            throw problem(HttpStatus.CONFLICT, ref + " was already reported with a different amount.");
        }
        return new Recorded(first.id(), ref, first.deliveries(), true);
    }

    private static final String DELIVERY = """
            SELECT d.id, d.event_id, e.type, e.object_ref AS payment_ref, w.url AS endpoint_url, d.status, d.attempts,
                   d.last_status_code, d.last_error, d.next_attempt_at, d.delivered_at
            FROM deliveries d JOIN events e ON e.id = d.event_id JOIN webhook_endpoints w ON w.id = d.endpoint_id
            WHERE w.merchant_id = :merchant""";

    /** shortcut: the newest 100, no paging; add a cursor (?after=id) when merchants have more. */
    List<Delivery> deliveries(long merchantId, Status status) {
        return jdbc.sql(DELIVERY + " AND (CAST(:status AS text) IS NULL OR d.status = :status) ORDER BY d.id DESC LIMIT 100")
                .param("merchant", merchantId).param("status", status == null ? null : status.name()).query(Delivery.class).list();
    }

    Optional<DeliveryLog> delivery(long merchantId, long id) {
        return jdbc.sql(DELIVERY + " AND d.id = :id").param("merchant", merchantId).param("id", id).query(Delivery.class).optional()
                .map(d -> new DeliveryLog(d, jdbc.sql("SELECT attempted_at, status_code, error, duration_ms FROM delivery_attempts WHERE delivery_id = ? ORDER BY id")
                        .param(id).query(Attempt.class).list()));
    }

    /** Challenge 1: a dead letter back to pending, due now, from the first attempt. Its old attempts stay in the log. */
    Delivery retry(long merchantId, long id) {
        int updated = jdbc.sql("""
                        UPDATE deliveries d SET status = 'PENDING', attempts = 0, next_attempt_at = ?
                        FROM webhook_endpoints w
                        WHERE w.id = d.endpoint_id AND w.merchant_id = ? AND d.id = ? AND d.status = 'FAILED'""")
                .params(now(), merchantId, id).update();
        Delivery delivery = delivery(merchantId, id).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such delivery.")).delivery();
        if (updated == 0) {
            throw problem(HttpStatus.CONFLICT, "Only a failed delivery can be retried; this one is " + delivery.status() + ".");
        }
        return delivery;
    }

    /** Challenge 2: a new secret. The old one keeps signing for 24 hours, so the merchant can switch over. */
    Endpoint rotateSecret(long merchantId, long endpointId) {
        return jdbc.sql("""
                        UPDATE webhook_endpoints SET previous_secret = secret, previous_secret_until = ?, secret = ?
                        WHERE id = ? AND merchant_id = ? RETURNING id, url, secret, created_at""")
                .params(now().plusHours(24), WebhookSignature.newSecret(), endpointId, merchantId).query(Endpoint.class).optional()
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such endpoint."));
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }

    private OffsetDateTime now() {
        return OffsetDateTime.now(clock).withOffsetSameInstant(ZoneOffset.UTC).truncatedTo(ChronoUnit.MICROS);
    }
}
