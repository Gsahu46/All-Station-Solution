package com.streamo.devices;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.UUID;

/** Device sessions and their refresh tokens: sign-in, refresh, sign-out, the device list. */
@Service
class Sessions {

    record Issued(long memberId, UUID sessionId, String scope, String refreshToken) {
    }

    record Device(UUID id, String name, String type, OffsetDateTime createdAt, OffsetDateTime lastUsedAt) {
    }

    private static final SecureRandom RANDOM = new SecureRandom();

    private final JdbcClient jdbc;
    private final PasswordEncoder encoder;
    private final Clock clock;
    private final Duration refreshLifetime;
    private final String dummyHash;

    Sessions(JdbcClient jdbc, PasswordEncoder encoder, Clock clock, @Value("${streamo.refresh-lifetime}") Duration refreshLifetime) {
        this.jdbc = jdbc;
        this.encoder = encoder;
        this.clock = clock;
        this.refreshLifetime = refreshLifetime;
        this.dummyHash = encoder.encode("no-such-member");
    }

    /** A TV in a living room can play, but only a phone or a browser may see and remove devices. */
    static String scopeFor(String deviceType) {
        return deviceType.equals("tv") ? "playback" : "playback devices";
    }

    @Transactional
    Optional<Issued> signIn(String email, String password, String deviceName, String deviceType) {
        Optional<Member> member = jdbc.sql("SELECT id, password_hash FROM members WHERE email = ?")
                .param(email.strip().toLowerCase(Locale.ROOT)).query(Member.class).optional();
        // Unknown email: still pay for one bcrypt check, so the answer takes as long as a wrong password.
        boolean matches = encoder.matches(password, member.map(Member::passwordHash).orElse(dummyHash));
        if (member.isEmpty() || !matches) {
            return Optional.empty();
        }
        UUID session = UUID.randomUUID();
        jdbc.sql("INSERT INTO device_sessions (id, member_id, device_name, device_type, created_at, last_used_at) VALUES (?, ?, ?, ?, ?, ?)")
                .params(session, member.get().id(), deviceName.strip(), deviceType, now(), now()).update();
        return Optional.of(new Issued(member.get().id(), session, scopeFor(deviceType), newRefreshToken(session)));
    }

    /**
     * Gives a new access token for a valid refresh token. The refresh token itself stays the same, so a phone on a
     * flaky network that retries never signs itself out.
     */
    @Transactional
    Optional<Issued> refresh(String refreshToken) {
        Optional<UUID> session = jdbc.sql("SELECT session_id FROM refresh_tokens WHERE token_hash = ? AND expires_at > ?")
                .params(sha256(refreshToken), now()).query(UUID.class).optional();
        if (session.isEmpty()) {
            return Optional.empty();
        }
        Optional<ActiveSession> active = jdbc.sql("UPDATE device_sessions SET last_used_at = ? WHERE id = ? AND revoked_at IS NULL RETURNING member_id, device_type")
                .params(now(), session.get()).query(ActiveSession.class).optional();
        return active.map(a -> new Issued(a.memberId(), session.get(), scopeFor(a.deviceType()), refreshToken));
    }

    boolean isActive(String sessionId) {
        try {
            return sessionId != null && jdbc.sql("SELECT EXISTS (SELECT 1 FROM device_sessions WHERE id = ? AND revoked_at IS NULL)")
                    .param(UUID.fromString(sessionId)).query(Boolean.class).single();
        } catch (IllegalArgumentException notAUuid) {
            return false;
        }
    }

    List<Device> devices(long memberId) {
        return jdbc.sql("SELECT id, device_name AS name, device_type AS type, created_at, last_used_at FROM device_sessions WHERE member_id = ? AND revoked_at IS NULL ORDER BY created_at, id")
                .param(memberId).query(Device.class).list();
    }

    /** Device ids are random UUIDs: nobody can guess another member's. */
    boolean remove(long memberId, UUID deviceId, String reason) {
        return jdbc.sql("UPDATE device_sessions SET revoked_at = ?, revoked_reason = ? WHERE id = ? AND revoked_at IS NULL")
                .params(now(), reason, deviceId).update() == 1;
    }

    /** 32 random bytes for the device; only their SHA-256 is stored, so a copy of the table opens nothing. */
    private String newRefreshToken(UUID session) {
        byte[] bytes = new byte[32];
        RANDOM.nextBytes(bytes);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
        OffsetDateTime created = now();   // one clock read: two would put expiry a few microseconds past the 30-day CHECK
        jdbc.sql("INSERT INTO refresh_tokens (token_hash, session_id, created_at, expires_at) VALUES (?, ?, ?, ?)")
                .params(sha256(token), session, created, created.plus(refreshLifetime)).update();
        return token;
    }

    private OffsetDateTime now() {
        return OffsetDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
    }

    static String sha256(String token) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private record Member(long id, String passwordHash) {
    }

    private record ActiveSession(long memberId, String deviceType) {
    }
}
