package com.tijori.otp;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

/**
 * One OTP request: replay check, limit, SMS. Each Idempotency-Key maps to one future result, created atomically,
 * so the same request sent twice, even at the same instant, books one slot and sends one SMS.
 */
@Service
class OtpService {

    static final Duration CODE_VALID_FOR = Duration.ofMinutes(5);

    record OtpRequest(String requestId, String mobile, Instant expiresAt, int attemptsLeft) {
    }

    /** The first request with a key stores its future here; any repeat waits for that same future. */
    private record Stored(String mobile, CompletableFuture<OtpRequest> result) {
    }

    private final OtpLimiter limiter;
    private final SmsSender sms;
    private final Clock clock;
    private final SecureRandom random = new SecureRandom();
    // shortcut: keys are kept until restart; a real store expires them after a day (a table or a cache with a TTL)
    private final Map<String, Stored> byKey = new ConcurrentHashMap<>();

    OtpService(OtpLimiter limiter, SmsSender sms, Clock clock) {
        this.limiter = limiter;
        this.sms = sms;
        this.clock = clock;
    }

    OtpRequest request(String idempotencyKey, String rawMobile) {
        String mobile = normalise(rawMobile);
        Stored seen = byKey.get(idempotencyKey);
        if (seen != null) {
            if (!seen.mobile().equals(mobile)) {
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Idempotency key reused",
                        "This Idempotency-Key was used for a different number. Use a new key for a new request.");
            }
            return seen.result().join();
        }
        OtpRequest result = issue(mobile);
        byKey.put(idempotencyKey, new Stored(mobile, CompletableFuture.completedFuture(result)));   // remember it for retries
        return result;
    }

    private OtpRequest issue(String mobile) {
        OtpLimiter.Decision d = limiter.check(mobile);
        if (!d.accepted()) {
            long seconds = Math.max(1, (d.retryAfter().toMillis() + 999) / 1000);   // round up: never invite an early retry
            ErrorResponseException tooMany = problem(HttpStatus.TOO_MANY_REQUESTS, "Too many OTP requests",
                    "This number has had " + OtpLimiter.MAX + " OTPs in the last 10 minutes. Try again in " + seconds + " seconds.");
            tooMany.getHeaders().set(HttpHeaders.RETRY_AFTER, String.valueOf(seconds));
            throw tooMany;
        }
        String code = String.format("%06d", random.nextInt(1_000_000));
        sms.send(mobile, "Your Tijori code is " + code + ". It expires in 5 minutes. Never share it.");
        limiter.book(mobile);   // only now: if the SMS provider had failed, the customer would keep the attempt
        return new OtpRequest("otp_" + UUID.randomUUID().toString().replace("-", ""), masked(mobile),
                clock.instant().plus(CODE_VALID_FOR).truncatedTo(java.time.temporal.ChronoUnit.SECONDS), d.attemptsLeft());
    }

    /** Keeps the digits; numbers with a country code or a leading 0 are accepted too. */
    static String normalise(String raw) {
        String digits = raw.replaceAll("\\D", "");
        if (!digits.matches("\\d{10,12}")) {
            throw problem(HttpStatus.BAD_REQUEST, "Invalid mobile number", "mobile must be an Indian mobile number of 10 digits.");
        }
        return digits;
    }

    static String masked(String mobile) {
        return "XXXXXX" + mobile.substring(6);
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }

    void clear() {
        byKey.clear();
    }
}
