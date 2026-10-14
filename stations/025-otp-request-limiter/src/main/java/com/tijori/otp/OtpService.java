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
import java.util.concurrent.CompletionException;
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
        Stored mine = new Stored(mobile, new CompletableFuture<>());
        Stored first = byKey.putIfAbsent(idempotencyKey, mine);
        if (first != null) {
            return replay(first, mobile);
        }
        try {
            OtpRequest result = issue(mobile);
            mine.result().complete(result);
            return result;
        } catch (RuntimeException refused) {
            byKey.remove(idempotencyKey);             // nothing happened: a later retry with this key may try again
            mine.result().completeExceptionally(refused);
            throw refused;
        }
    }

    private OtpRequest replay(Stored first, String mobile) {
        if (!first.mobile().equals(mobile)) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Idempotency key reused",
                    "This Idempotency-Key was used for a different number. Use a new key for a new request.");
        }
        try {
            return first.result().join();             // the same answer as the first request, even if it is still running
        } catch (CompletionException e) {
            throw (RuntimeException) e.getCause();
        }
    }

    private OtpRequest issue(String mobile) {
        OtpLimiter.Decision d = limiter.tryAcquire(mobile);
        if (!d.accepted()) {
            long seconds = Math.max(1, (d.retryAfter().toMillis() + 999) / 1000);   // round up: never invite an early retry
            ErrorResponseException tooMany = problem(HttpStatus.TOO_MANY_REQUESTS, "Too many OTP requests",
                    "This number has had " + OtpLimiter.MAX + " OTPs in the last 10 minutes. Try again in " + seconds + " seconds.");
            tooMany.getHeaders().set(HttpHeaders.RETRY_AFTER, String.valueOf(seconds));
            throw tooMany;
        }
        String code = String.format("%06d", random.nextInt(1_000_000));
        sms.send(mobile, "Your Tijori code is " + code + ". It expires in 5 minutes. Never share it.");
        return new OtpRequest("otp_" + UUID.randomUUID().toString().replace("-", ""), masked(mobile),
                clock.instant().plus(CODE_VALID_FOR).truncatedTo(java.time.temporal.ChronoUnit.SECONDS), d.attemptsLeft());
    }

    /** "+91 98765-43210", "098765 43210" and "9876543210" are one number, so formats cannot dodge the limit. */
    static String normalise(String raw) {
        String digits = raw.replaceAll("[\\s()-]", "");
        if (digits.startsWith("+91")) {
            digits = digits.substring(3);
        } else if (digits.length() == 11 && digits.startsWith("0")) {
            digits = digits.substring(1);
        }
        if (!digits.matches("[6-9]\\d{9}")) {
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
