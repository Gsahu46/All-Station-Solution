package com.taskloom.welcome;

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

    Listeners(WelcomeMailer mailer, CrmClient crm) {
        this.mailer = mailer;
        this.crm = crm;
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
