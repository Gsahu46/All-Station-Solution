package com.tijori.passkeys;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Locale;
import java.util.Optional;

/** The fallback: password and a code from an authenticator app. Never a password alone, never an SMS. */
@Service
class CodeSignIn {

    private final JdbcClient jdbc;
    private final PasswordEncoder encoder;
    private final Clock clock;
    private final String dummyHash;

    CodeSignIn(JdbcClient jdbc, PasswordEncoder encoder, Clock clock) {
        this.jdbc = jdbc;
        this.encoder = encoder;
        this.clock = clock;
        this.dummyHash = encoder.encode("no-such-customer");
    }

    private record Customer(long id, String passwordHash, byte[] totpSecret) {
    }

    /** Demo rule: 5 wrong codes in a row lock code sign-in for 15 minutes. */
    static final int MAX_WRONG_CODES = 5;
    static final Duration LOCK = Duration.ofMinutes(15);

    /**
     * The customer's id if the password is right, code sign-in is not locked, and the code is the current one (or
     * the one before) and unused. A wrong code counts (a used one does not: it is a replay, not a guess); the fifth locks; a good sign-in resets the count.
     */
    @Transactional
    Optional<Long> signIn(String email, String password, String code) {
        Optional<Customer> customer = jdbc.sql("SELECT id, password_hash, totp_secret FROM customers WHERE email = ? FOR UPDATE")
                .param(email.strip().toLowerCase(Locale.ROOT)).query(Customer.class).optional();
        boolean passwordOk = encoder.matches(password, customer.map(Customer::passwordHash).orElse(dummyHash));
        if (customer.isEmpty() || !passwordOk) {
            return Optional.empty();
        }
        long id = customer.get().id();
        OffsetDateTime now = OffsetDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
        if (jdbc.sql("SELECT codes_locked_until > ? FROM customers WHERE id = ?").params(now, id).query(Boolean.class).optional().orElse(false)) {
            return Optional.empty();   // the same answer as a wrong code: nothing tells a guesser they are locked out
        }
        long step = Totp.step(now.toEpochSecond());
        for (long s = step; s >= step - 1; s--) {
            if (MessageDigest.isEqual(Totp.code(customer.get().totpSecret(), s).getBytes(StandardCharsets.US_ASCII), code.getBytes(StandardCharsets.US_ASCII))) {
                Optional<Long> ok = jdbc.sql("UPDATE customers SET totp_last_step = ?, failed_codes = 0, codes_locked_until = NULL WHERE id = ? AND (totp_last_step IS NULL OR totp_last_step < ?) RETURNING id")
                        .params(s, id, s).query(Long.class).optional();
                return ok;   // empty if already used: a replay, not a guess, so it does not count
            }
        }
        jdbc.sql("""
                UPDATE customers SET failed_codes = CASE WHEN failed_codes + 1 >= ? THEN 0 ELSE failed_codes + 1 END,
                                     codes_locked_until = CASE WHEN failed_codes + 1 >= ? THEN ? ELSE codes_locked_until END
                WHERE id = ?""").params(MAX_WRONG_CODES, MAX_WRONG_CODES, now.plus(LOCK), id).update();
        return Optional.empty();
    }
}
