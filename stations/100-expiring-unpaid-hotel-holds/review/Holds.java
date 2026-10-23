package com.ghoomo.holds;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Duration;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

@Service
class Holds {

    record Hold(long id, long roomTypeId, LocalDate date, String status, OffsetDateTime expiresAt) {
    }

    record Created(Hold hold, boolean replay) {
    }

    private final JdbcClient jdbc;
    private final Clock clock;
    private final Duration ttl;

    Holds(JdbcClient jdbc, Clock clock, @Value("${ghoomo.holds.ttl}") Duration ttl) {
        this.jdbc = jdbc;
        this.clock = clock;
        this.ttl = ttl;
    }

    private static final String HOLD = "SELECT id, room_type_id, stay_date AS date, status, expires_at FROM holds";

    /**
     * Takes a room and records the hold, in one transaction. The same Idempotency-Key with the same request returns
     * the first hold; with another request it is a 422.
     */
    @Transactional
    Created create(String key, long roomTypeId, LocalDate date, String guestEmail) {
        String email = guestEmail.strip().toLowerCase(Locale.ROOT);
        String hash = sha256(roomTypeId + "|" + date + "|" + email);
        Optional<Created> replay = replay(key, hash);
        if (replay.isPresent()) {
            return replay.get();
        }
        // Clearer in two steps: is a room free? Then take it.
        record Night(int total, int held) {
        }
        Night night = jdbc.sql("SELECT total, held FROM room_nights WHERE room_type_id = ? AND stay_date = ?").params(roomTypeId, date)
                .query(Night.class).optional().orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such room type or night."));
        if (night.held() >= night.total()) {
            throw problem(HttpStatus.CONFLICT, "No room of this type is free that night.");
        }
        jdbc.sql("UPDATE room_nights SET held = held + 1 WHERE room_type_id = ? AND stay_date = ?").params(roomTypeId, date).update();
        OffsetDateTime now = now();
        long id = jdbc.sql("""
                        INSERT INTO holds (idempotency_key, request_hash, room_type_id, stay_date, guest_email, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id""")
                .params(key, hash, roomTypeId, date, email, now, now.plus(ttl)).query(Long.class).single();
        return new Created(find(id).orElseThrow(), false);
    }

    /** The first hold made with this key, if any. */
    Optional<Created> replay(String key, String hash) {
        record Stored(long id, String requestHash) {
        }
        return jdbc.sql("SELECT id, request_hash FROM holds WHERE idempotency_key = ?").param(key).query(Stored.class).optional().map(s -> {
            if (!s.requestHash().equals(hash)) {
                throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "This Idempotency-Key was already used for a different hold.");
            }
            return new Created(find(s.id()).orElseThrow(), true);
        });
    }

    Optional<Hold> find(long id) {
        return jdbc.sql(HOLD + " WHERE id = ?").param(id).query(Hold.class).optional();
    }

    /** Expires every hold that is due and gives its room back. synchronized, so it never runs twice at once. */
    @Transactional
    synchronized int expireDue() {
        record Due(long id, long roomTypeId, LocalDate stayDate) {
        }
        OffsetDateTime now = now();
        List<Due> due = jdbc.sql("SELECT id, room_type_id, stay_date FROM holds WHERE status = 'HELD' AND expires_at <= ?")
                .param(now).query(Due.class).list();
        for (Due d : due) {
            jdbc.sql("UPDATE room_nights SET held = held - 1 WHERE room_type_id = ? AND stay_date = ?").params(d.roomTypeId(), d.stayDate()).update();
            jdbc.sql("UPDATE holds SET status = 'EXPIRED', expired_at = ? WHERE id = ?").params(now, d.id()).update();
        }
        return due.size();
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }

    static String sha256(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private OffsetDateTime now() {
        return OffsetDateTime.now(clock).withOffsetSameInstant(ZoneOffset.UTC).truncatedTo(ChronoUnit.MICROS);
    }
}
