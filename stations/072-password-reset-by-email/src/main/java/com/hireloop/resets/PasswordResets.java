package com.hireloop.resets;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.HexFormat;
import java.util.Locale;
import java.util.Optional;

@Service
class PasswordResets {

    /** Demo rule: at most 3 links waiting at once per account, so the form cannot flood someone's inbox. */
    static final int MAX_OPEN_LINKS = 3;

    private static final SecureRandom RANDOM = new SecureRandom();

    private final JdbcClient jdbc;
    private final PasswordEncoder passwords;
    private final Clock clock;
    private final String link;
    private final Duration validFor;

    PasswordResets(JdbcClient jdbc, PasswordEncoder passwords, Clock clock,
                   @Value("${hireloop.reset-link}") String link, @Value("${hireloop.reset-valid-minutes}") long minutes) {
        this.jdbc = jdbc;
        this.passwords = passwords;
        this.clock = clock;
        this.link = link;
        this.validFor = Duration.ofMinutes(minutes);
    }

    /**
     * Sends a link if, and only if, an active account has this email. The caller never learns which: the controller
     * gives one reply for every case.
     */
    @Transactional
    void request(String typedEmail) {
        String email = typedEmail.strip().toLowerCase(Locale.ROOT);
        Instant now = clock.instant();
        Optional<Long> candidate = jdbc.sql("SELECT id FROM candidates WHERE email = ? AND status = 'ACTIVE' FOR UPDATE").param(email).query(Long.class).optional();
        if (candidate.isEmpty()) {
            return;
        }
        long open = jdbc.sql("SELECT count(*) FROM password_resets WHERE candidate_id = ? AND used_at IS NULL AND expires_at > ?")
                .params(candidate.get(), utc(now)).query(Long.class).single();
        if (open >= MAX_OPEN_LINKS) {
            return;
        }
        byte[] secret = new byte[32];   // 256 random bits: guessing one is hopeless
        RANDOM.nextBytes(secret);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(secret);
        jdbc.sql("INSERT INTO password_resets (candidate_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)")
                .params(candidate.get(), sha256(token), utc(now), utc(now.plus(validFor))).update();
        jdbc.sql("INSERT INTO outbox_emails (to_email, subject, body, created_at) VALUES (?, ?, ?, ?)")
                .params(email, "Reset your Hireloop password",
                        "Someone asked to reset the password for this account. If it was you, open this link within "
                                + validFor.toMinutes() + " minutes:\n" + link + token + "\nIf it was not you, ignore this email.", utc(now)).update();
    }

    /**
     * Uses the link: one UPDATE both checks it (unused, not expired) and marks it used, so two requests with the same
     * link cannot both pass. Then the password changes and every other open link for the account stops working.
     */
    @Transactional
    void complete(String token, String newPassword) {
        Instant now = clock.instant();
        Long candidate = token.matches("[A-Za-z0-9_-]{43}") ? jdbc.sql("""
                        UPDATE password_resets SET used_at = ? WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?
                        RETURNING candidate_id""").params(utc(now), sha256(token), utc(now)).query(Long.class).optional().orElse(null) : null;
        if (candidate == null) {
            // One message for unknown, used and expired links: none of them says anything about the account.
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "This link is invalid or has expired; ask for a new one");
        }
        jdbc.sql("UPDATE candidates SET password_hash = ? WHERE id = ?").params(passwords.encode(newPassword), candidate).update();
        jdbc.sql("DELETE FROM password_resets WHERE candidate_id = ? AND used_at IS NULL").param(candidate).update();
    }

    static String sha256(String token) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.US_ASCII)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static OffsetDateTime utc(Instant instant) {
        return instant.atOffset(ZoneOffset.UTC);
    }
}
