package com.tijori.passkeys;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
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

    /**
     * The customer's id if the password is right and the code is the current one (or the one before, for a slow
     * phone clock) and has not been used yet. Using it moves totp_last_step forward in one conditional UPDATE, so
     * of two requests with the same code exactly one gets through.
     */
    Optional<Long> signIn(String email, String password, String code) {
        Optional<Customer> customer = jdbc.sql("SELECT id, password_hash, totp_secret FROM customers WHERE email = ?")
                .param(email.strip().toLowerCase(Locale.ROOT)).query(Customer.class).optional();
        boolean passwordOk = encoder.matches(password, customer.map(Customer::passwordHash).orElse(dummyHash));
        if (customer.isEmpty() || !passwordOk) {
            return Optional.empty();
        }
        long now = Totp.step(clock.instant().getEpochSecond());
        for (long step = now; step >= now - 1; step--) {
            if (MessageDigest.isEqual(Totp.code(customer.get().totpSecret(), step).getBytes(StandardCharsets.US_ASCII), code.getBytes(StandardCharsets.US_ASCII))) {
                return jdbc.sql("UPDATE customers SET totp_last_step = ? WHERE id = ? AND (totp_last_step IS NULL OR totp_last_step < ?) RETURNING id")
                        .params(step, customer.get().id(), step).query(Long.class).optional();
            }
        }
        return Optional.empty();
    }
}
