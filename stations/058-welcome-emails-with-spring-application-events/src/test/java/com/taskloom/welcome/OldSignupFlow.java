package com.taskloom.welcome;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.event.EventListener;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;

/**
 * The sign-up as it shipped, kept only in tests (registered as beans by the trap test). Same steps as today; the
 * difference is the listener: a plain @EventListener runs at once, inside publishEvent, before the transaction ends.
 */
class OldSignupFlow {

    record OldSignedUp(long signupId, String email, String name) {
    }

    private final JdbcClient jdbc;
    private final ApplicationEventPublisher events;

    OldSignupFlow(JdbcClient jdbc, ApplicationEventPublisher events) {
        this.jdbc = jdbc;
        this.events = events;
    }

    @Transactional
    public void signUp(String email, String name, String invite) {
        long id = jdbc.sql("INSERT INTO signups (email, name) VALUES (?, ?) RETURNING id").params(email, name).query(Long.class).single();
        events.publishEvent(new OldSignedUp(id, email, name));   // the email goes out right here
        if (jdbc.sql("UPDATE invites SET seats_used = seats_used + 1 WHERE code = ? AND seats_used < seats_total").param(invite).update() == 0) {
            throw new IllegalStateException("invite full");      // ...and the sign-up rolls back after it
        }
    }

    static class OldWelcomeListener {

        private final MailGateway mail;

        OldWelcomeListener(MailGateway mail) {
            this.mail = mail;
        }

        @EventListener
        public void send(OldSignedUp e) {
            mail.send(WelcomeEmail.to(e.email(), e.name()));
        }
    }
}
