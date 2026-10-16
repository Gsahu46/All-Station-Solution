package com.taskloom.welcome;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/**
 * Sends one welcome email per sign-up, even if the event arrives twice: it claims the email in the sent_emails table
 * first. A failing provider is retried with growing waits; after the last attempt the email is marked DEAD (the
 * dead-letter state) for a person to look at, instead of being retried forever or lost.
 */
@Component
class WelcomeMailer {

    private static final Logger log = LoggerFactory.getLogger(WelcomeMailer.class);

    private final JdbcClient jdbc;
    private final MailGateway mail;
    private final int attempts;
    private final long backoffMs;

    WelcomeMailer(JdbcClient jdbc, MailGateway mail, @Value("${taskloom.mail.attempts}") int attempts, @Value("${taskloom.mail.backoff-ms}") long backoffMs) {
        this.jdbc = jdbc;
        this.mail = mail;
        this.attempts = attempts;
        this.backoffMs = backoffMs;
    }

    void sendOnce(SignedUp e) {
        int claimed = jdbc.sql("INSERT INTO sent_emails (signup_id, kind, status) VALUES (?, 'WELCOME', 'SENDING') ON CONFLICT DO NOTHING").param(e.signupId()).update();
        if (claimed == 0) {
            log.info("Welcome email for sign-up {} already claimed: duplicate event ignored", e.signupId());
            return;
        }
        MailGateway.Message message = WelcomeEmail.to(e.email(), e.name());
        for (int attempt = 1; attempt <= attempts; attempt++) {
            try {
                mail.send(message);
                jdbc.sql("UPDATE sent_emails SET status = 'SENT', attempts = ? WHERE signup_id = ? AND kind = 'WELCOME'").params(attempt, e.signupId()).update();
                log.info("Welcome email for sign-up {} sent on attempt {} (simulated: recorded in the mailbox)", e.signupId(), attempt);
                return;
            } catch (RuntimeException failure) {
                String error = String.valueOf(failure.getMessage());
                jdbc.sql("UPDATE sent_emails SET attempts = ?, last_error = ? WHERE signup_id = ? AND kind = 'WELCOME'")
                        .params(attempt, error.length() > 200 ? error.substring(0, 200) : error, e.signupId()).update();
                log.warn("Welcome email for sign-up {} failed, attempt {} of {}: {}", e.signupId(), attempt, attempts, error);
                if (attempt < attempts) {
                    pause(backoffMs * attempt);
                }
            }
        }
        jdbc.sql("UPDATE sent_emails SET status = 'DEAD' WHERE signup_id = ? AND kind = 'WELCOME'").param(e.signupId()).update();
    }

    private static void pause(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
        }
    }
}
