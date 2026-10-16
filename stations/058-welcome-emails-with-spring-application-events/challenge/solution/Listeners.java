package com.taskloom.welcome;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * The two things a sign-up causes. Both run only AFTER the sign-up's transaction commits (a rolled-back sign-up
 * causes nothing), and both on another thread (a slow CRM does not slow the sign-up). Limit: the event lives in
 * memory, so a crash between commit and listener loses it; a transactional outbox closes that gap.
 */
@Component
class Listeners {

    private final WelcomeMailer mailer;
    private final CrmClient crm;
    private final JdbcClient jdbc;

    Listeners(WelcomeMailer mailer, CrmClient crm, JdbcClient jdbc) {
        this.mailer = mailer;
        this.crm = crm;
        this.jdbc = jdbc;
    }

    /** A new reaction to sign-ups is a new listener: SignupService does not change. */
    @Async
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void countForAnalytics(SignedUp e) {
        jdbc.sql("INSERT INTO analytics_events (name, signup_id) VALUES ('signed_up', ?)").param(e.signupId()).update();
    }

    @Async
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void sendWelcomeEmail(SignedUp e) {
        mailer.sendOnce(e);
    }

    @Async
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void registerInCrm(SignedUp e) {
        crm.register(e.signupId(), e.email(), e.name());
    }
}
