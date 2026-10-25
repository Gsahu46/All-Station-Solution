package com.basketo.referrals;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * Sends the outbox's wallet credits. Each credit carries its reward's id as Idempotency-Key, so a credit sent again
 * after a lost answer is not paid twice (if the wallet honours the key). Failures that may pass are tried again later,
 * further apart each time; after the last try, or when the wallet refuses the request itself, the credit is DEAD: kept,
 * with its last error, for a person. Rows are claimed for a minute, so no transaction is open during the call, and
 * two app instances never send the same row at once.
 */
@Component
class WalletRelay {

    private static final Logger log = LoggerFactory.getLogger(WalletRelay.class);
    private final JdbcClient jdbc;
    private final RestClient wallet;
    private final int maxAttempts;
    private final Duration firstRetryAfter;

    WalletRelay(JdbcClient jdbc, @Value("${basketo.wallet.url}") String url, @Value("${basketo.wallet.timeout}") Duration timeout,
                @Value("${basketo.wallet.max-attempts}") int maxAttempts, @Value("${basketo.wallet.first-retry-after}") Duration firstRetryAfter) {
        this.jdbc = jdbc;
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(HttpClient.newBuilder().connectTimeout(timeout).build());
        factory.setReadTimeout(timeout);
        this.wallet = RestClient.builder().baseUrl(url).requestFactory(factory).build();
        this.maxAttempts = maxAttempts;
        this.firstRetryAfter = firstRetryAfter;
    }

    record Due(long id, long rewardId, int attempts, long referrerId, long amountPaise) {
    }

    @Scheduled(fixedDelayString = "${basketo.wallet.poll-every}")
    void sendDue() {
        List<Due> due = jdbc.sql("""
                UPDATE wallet_outbox o SET claimed_until = now() + interval '1 minute'
                FROM rewards r
                WHERE r.id = o.reward_id AND o.id IN (
                    SELECT id FROM wallet_outbox WHERE status = 'PENDING' AND next_attempt_at <= now()
                      AND (claimed_until IS NULL OR claimed_until < now())
                    ORDER BY id LIMIT 20 FOR UPDATE SKIP LOCKED)
                RETURNING o.id, o.reward_id, o.attempts, r.referrer_id, r.amount_paise""").query(Due.class).list();
        due.forEach(this::send);
    }

    private void send(Due d) {
        try {
            wallet.post().uri("/credits").header("Idempotency-Key", "referral-reward-" + d.rewardId())
                    .body(Map.of("customerId", d.referrerId(), "amountPaise", d.amountPaise(), "reason", "referral reward"))
                    .retrieve().toBodilessEntity();
            jdbc.sql("UPDATE wallet_outbox SET status = 'SENT', attempts = attempts + 1, sent_at = now(), claimed_until = NULL, last_error = NULL WHERE id = ?")
                    .param(d.id()).update();
        } catch (HttpClientErrorException e) {
            int status = e.getStatusCode().value();
            if (status == 408 || status == 429) {
                retryLater(d, e.getMessage());
            } else {
                dead(d, "the wallet refused the credit: " + status);
            }
        } catch (RestClientException e) {
            retryLater(d, e.getMessage());
        }
    }

    private void retryLater(Due d, String error) {
        int attempts = d.attempts() + 1;
        if (attempts >= maxAttempts) {
            dead(d, "gave up after " + attempts + " tries: " + error);
            return;
        }
        long waitMillis = firstRetryAfter.toMillis() << (attempts - 1);   // 1 s, 2 s, 4 s, ...
        jdbc.sql("UPDATE wallet_outbox SET attempts = ?, last_error = ?, claimed_until = NULL, next_attempt_at = now() + ? * interval '1 millisecond' WHERE id = ?")
                .params(attempts, error, waitMillis, d.id()).update();
    }

    private void dead(Due d, String error) {
        jdbc.sql("UPDATE wallet_outbox SET status = 'DEAD', attempts = attempts + 1, last_error = ?, claimed_until = NULL WHERE id = ?")
                .params(error, d.id()).update();
        log.error("Wallet credit for reward {} is DEAD: {}", d.rewardId(), error);   // a person must look at it
    }
}
