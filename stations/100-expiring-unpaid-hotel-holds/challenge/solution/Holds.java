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
        // One statement takes a room only if one is free: two guests cannot both take the last one.
        int taken = jdbc.sql("UPDATE room_nights SET held = held + 1 WHERE room_type_id = ? AND stay_date = ? AND held < total")
                .params(roomTypeId, date).update();
        if (taken == 0) {
            boolean exists = jdbc.sql("SELECT count(*) FROM room_nights WHERE room_type_id = ? AND stay_date = ?").params(roomTypeId, date).query(Long.class).single() > 0;
            throw exists ? problem(HttpStatus.CONFLICT, "No room of this type is free that night.") : problem(HttpStatus.NOT_FOUND, "No such room type or night.");
        }
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

    /**
     * Expires every hold that is due and gives its room back, in one transaction. Safe to run on every server at the
     * same moment: a hold is expired only while it is still HELD, locked rows are skipped, so each room is given
     * back once. Returns how many holds this run expired.
     */
    @Transactional
    int expireDue() {
        record Released(long roomTypeId, LocalDate stayDate) {
        }
        List<Released> released = jdbc.sql("""
                        UPDATE holds SET status = 'EXPIRED', expired_at = :now
                        WHERE id IN (SELECT id FROM holds WHERE status = 'HELD' AND expires_at <= :now
                                     ORDER BY expires_at LIMIT 500 FOR UPDATE SKIP LOCKED)
                          AND status = 'HELD'
                        RETURNING room_type_id, stay_date""")
                .param("now", now()).query(Released.class).list();
        for (Released r : released) {
            jdbc.sql("UPDATE room_nights SET held = held - 1 WHERE room_type_id = ? AND stay_date = ?").params(r.roomTypeId(), r.stayDate()).update();
        }
        return released.size();
    }

    /**
     * Challenge 1: the guest paid (simulated). Only a hold that is still within its time; confirming twice is fine.
     */
    @Transactional
    Hold confirm(long id) {
        int confirmed = jdbc.sql("""
                        UPDATE holds SET status = 'CONFIRMED'
                        WHERE id = ? AND (status = 'CONFIRMED' OR (status = 'HELD' AND expires_at > ?))""")
                .params(id, now()).update();
        Hold hold = find(id).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such hold."));
        if (confirmed == 0) {
            throw problem(HttpStatus.CONFLICT, "Too late: this hold has expired.");
        }
        return hold;
    }

    /** Challenge 2: the room goes back once, however many times this runs: only the run that cancels a HELD hold gives it back. */
    @Transactional
    void cancel(long id) {
        record Released(long roomTypeId, LocalDate stayDate) {
        }
        Optional<Released> released = jdbc.sql("UPDATE holds SET status = 'CANCELLED' WHERE id = ? AND status = 'HELD' RETURNING room_type_id, stay_date")
                .param(id).query(Released.class).optional();
        if (released.isPresent()) {
            jdbc.sql("UPDATE room_nights SET held = held - 1 WHERE room_type_id = ? AND stay_date = ?")
                    .params(released.get().roomTypeId(), released.get().stayDate()).update();
        } else if (find(id).isEmpty()) {
            throw problem(HttpStatus.NOT_FOUND, "No such hold.");
        }
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
