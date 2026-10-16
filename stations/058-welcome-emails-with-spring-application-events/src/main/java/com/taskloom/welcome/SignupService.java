package com.taskloom.welcome;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.util.Optional;

/**
 * Sign-up knows nothing about email, the CRM or analytics: it saves the sign-up, says so with an event, and
 * finishes. Whatever listens decides what happens next.
 */
@Service
class SignupService {

    record Signup(long id, String email, String name, String welcomeEmail) {
    }

    private final JdbcClient jdbc;
    private final ApplicationEventPublisher events;

    SignupService(JdbcClient jdbc, ApplicationEventPublisher events) {
        this.jdbc = jdbc;
        this.events = events;
    }

    @Transactional
    Signup signUp(String email, String name, String inviteCode) {
        long id;
        try {
            id = jdbc.sql("INSERT INTO signups (email, name) VALUES (?, ?) RETURNING id").params(email, name).query(Long.class).single();
        } catch (DuplicateKeyException e) {
            throw problem(HttpStatus.CONFLICT, "Already signed up", email + " has already signed up.");
        }
        events.publishEvent(new SignedUp(id, email, name));   // nothing happens yet for after-commit listeners
        if (inviteCode != null) {
            joinTeam(id, inviteCode);   // can still fail, and roll everything back, after the event was published
        }
        return new Signup(id, email, name, "PENDING");
    }

    private void joinTeam(long signupId, String code) {
        int seated = jdbc.sql("UPDATE invites SET seats_used = seats_used + 1 WHERE code = ? AND seats_used < seats_total").param(code).update();
        if (seated == 0) {
            boolean exists = jdbc.sql("SELECT count(*) FROM invites WHERE code = ?").param(code).query(Long.class).single() > 0;
            throw exists ? problem(HttpStatus.CONFLICT, "Invite full", "Invite " + code + " has no seats left.")
                    : problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown invite", "No invite " + code + ".");
        }
        jdbc.sql("UPDATE signups SET invite_code = ? WHERE id = ?").params(code, signupId).update();
    }

    Optional<Signup> find(long id) {
        return jdbc.sql("""
                SELECT s.id, s.email, s.name, coalesce(e.status, 'PENDING') AS welcome_email
                FROM signups s LEFT JOIN sent_emails e ON e.signup_id = s.id AND e.kind = 'WELCOME' WHERE s.id = ?""")
                .param(id).query(Signup.class).optional();
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
