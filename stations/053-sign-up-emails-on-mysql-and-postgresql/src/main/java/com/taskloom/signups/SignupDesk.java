package com.taskloom.signups;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;

import java.util.Locale;
import java.util.Optional;

/**
 * Sign-ups on either database. The email is kept as the person typed it; "the same email" means the same after
 * lower-casing, on both databases, because both schemas index lower(email) and the queries compare lower(email).
 */
@Service
class SignupDesk {

    record Signup(long id, String email, String name) {
    }

    private final JdbcClient jdbc;

    SignupDesk(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    Signup signUp(String email, String name) {
        if (findByEmail(email).isPresent()) {
            throw taken(email);
        }
        KeyHolder key = new GeneratedKeyHolder();
        try {
            jdbc.sql("INSERT INTO signups (email, name) VALUES (?, ?)").params(email, name).update(key, "id");
        } catch (DuplicateKeyException e) {
            // Two sign-ups with the same email at the same moment both pass the check; the unique index stops one.
            throw taken(email);
        }
        return new Signup(key.getKey().longValue(), email, name);
    }

    Optional<Signup> find(long id) {
        return jdbc.sql("SELECT id, email, name FROM signups WHERE id = ?").param(id).query(Signup.class).optional();
    }

    /** lower(email) = ? matches the expression index on both databases, so this is an index lookup. */
    Optional<Signup> findByEmail(String email) {
        return jdbc.sql("SELECT id, email, name FROM signups WHERE lower(email) = ?").param(email.toLowerCase(Locale.ROOT))
                .query(Signup.class).optional();
    }

    private static ErrorResponseException taken(String email) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, email + " has already signed up (emails are compared ignoring case).");
        p.setTitle("Already signed up");
        return new ErrorResponseException(HttpStatus.CONFLICT, p, null);
    }
}
