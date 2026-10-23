package com.paysetu.webhooks;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.io.IOException;
import java.net.ConnectException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Executors;

/**
 * Works through the outbox: claims the deliveries that are due, sends each one signed, and records every attempt.
 * Several servers may run it at once: a claimed delivery is invisible to the others until its lease ends.
 */
@Component
class Dispatcher {

    static final int MAX_ATTEMPTS = 8;   // also the deliveries_attempts_range constraint
    static final int BATCH = 20;
    private static final Logger log = LoggerFactory.getLogger(Dispatcher.class);

    private final JdbcClient jdbc;
    private final Clock clock;
    private final TransactionTemplate tx;
    private final Duration firstRetry;
    private final Duration timeout;
    private final HttpClient http;

    Dispatcher(JdbcClient jdbc, Clock clock, PlatformTransactionManager transactions,
               @Value("${paysetu.webhooks.first-retry}") Duration firstRetry, @Value("${paysetu.webhooks.timeout}") Duration timeout) {
        this.jdbc = jdbc;
        this.clock = clock;
        this.tx = new TransactionTemplate(transactions);
        this.firstRetry = firstRetry;
        this.timeout = timeout;
        // Redirects are not followed: the merchant registered this URL, not wherever it points us next.
        this.http = HttpClient.newBuilder().connectTimeout(timeout).followRedirects(HttpClient.Redirect.NEVER).build();
    }

    record Due(long id, int attempts, UUID eventId, String payload, String url, String secret, String previousSecret) {
    }

    /** One round. Returns how many deliveries it tried. */
    int dispatchDue() {
        List<Due> due = claim(now());
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {   // one slow merchant does not hold up the rest
            for (Due d : due) {
                threads.execute(() -> {
                    try {
                        attempt(d);
                    } catch (RuntimeException e) {
                        log.warn("Delivery {} could not be recorded; it is tried again when its lease ends", d.id(), e);
                    }
                });
            }
        }
        return due.size();
    }

    /**
     * One statement: the due rows are locked (rows another server has locked are skipped) and their next attempt
     * moved past the lease, so no other round picks them up while we send.
     */
    private List<Due> claim(OffsetDateTime now) {
        return jdbc.sql("""
                        UPDATE deliveries d SET next_attempt_at = :leaseEnd
                        FROM events e, webhook_endpoints w
                        WHERE d.id IN (SELECT id FROM deliveries
                                       WHERE status = 'PENDING' AND next_attempt_at <= :now
                                       ORDER BY next_attempt_at, id LIMIT :batch
                                       FOR UPDATE SKIP LOCKED)
                          AND e.id = d.event_id AND w.id = d.endpoint_id
                        RETURNING d.id, d.attempts, e.id AS event_id, e.payload, w.url, w.secret,
                                  CASE WHEN w.previous_secret_until > :now THEN w.previous_secret END AS previous_secret""")
                .param("now", now).param("leaseEnd", now.plus(timeout).plusSeconds(30)).param("batch", BATCH)
                .query(Due.class).list();
    }

    private void attempt(Due d) {
        OffsetDateTime at = now();
        String id = d.eventId().toString();
        long timestamp = at.toEpochSecond();
        HttpRequest request = HttpRequest.newBuilder(URI.create(d.url())).timeout(timeout)
                .header("Content-Type", "application/json")
                .header("User-Agent", "Paysetu-Webhooks/1.0")
                .header("webhook-id", id)   // the same on every retry: the merchant drops repeats by it
                .header("webhook-timestamp", Long.toString(timestamp))
                .header("webhook-signature", WebhookSignature.sign(d.secret(), id, timestamp, d.payload())
                        + (d.previousSecret() == null ? "" : " " + WebhookSignature.sign(d.previousSecret(), id, timestamp, d.payload())))
                .POST(HttpRequest.BodyPublishers.ofString(d.payload())).build();
        long started = System.nanoTime();
        Integer code = null;
        String error = null;
        try {
            code = http.send(request, HttpResponse.BodyHandlers.discarding()).statusCode();
            if (code / 100 != 2) {
                error = "HTTP " + code + (code / 100 == 3 ? " (redirects are not followed)" : "");
            }
        } catch (HttpTimeoutException e) {
            error = "timed out after " + timeout.toMillis() + " ms";
        } catch (ConnectException e) {
            error = "could not connect";
        } catch (IOException e) {
            error = e.getClass().getSimpleName();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return;   // nothing recorded: tried again when the lease ends
        }
        record(d, at, code, error, (int) ((System.nanoTime() - started) / 1_000_000));
    }

    private void record(Due d, OffsetDateTime at, Integer code, String error, int durationMs) {
        int attempts = d.attempts() + 1;
        String status = error == null ? "DELIVERED" : attempts >= MAX_ATTEMPTS ? "FAILED" : "PENDING";
        OffsetDateTime next = status.equals("PENDING") ? at.plus(backoff(firstRetry, attempts)) : null;
        tx.executeWithoutResult(s -> {
            jdbc.sql("INSERT INTO delivery_attempts (delivery_id, attempted_at, status_code, error, duration_ms) VALUES (?, ?, ?, ?, ?)")
                    .params(d.id(), at, code, error, durationMs).update();
            int updated = jdbc.sql("""
                            UPDATE deliveries SET status = ?, attempts = ?, next_attempt_at = ?, last_status_code = ?, last_error = ?, delivered_at = ?
                            WHERE id = ? AND attempts = ?""")
                    .params(status, attempts, next, code, error, status.equals("DELIVERED") ? at : null, d.id(), d.attempts()).update();
            if (updated != 1) {   // the lease ran out and another round recorded this attempt: keep theirs
                throw new IllegalStateException("delivery " + d.id() + " was recorded by another round");
            }
        });
    }

    /** After the n-th failure: first-retry, then twice as long each time (30 s, 1 min, 2 min, ... 32 min). */
    static Duration backoff(Duration firstRetry, int failedAttempts) {
        return firstRetry.multipliedBy(1L << (failedAttempts - 1));
    }

    private OffsetDateTime now() {
        return OffsetDateTime.now(clock).withOffsetSameInstant(ZoneOffset.UTC).truncatedTo(ChronoUnit.MICROS);
    }
}
