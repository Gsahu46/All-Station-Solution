# Station 058 plan: Welcome emails with Spring application events

**Problem.** Taskloom's sign-up called email, CRM and analytics directly: a slow CRM made sign-up slow. A first move
to events used a plain @EventListener: it ran inside publishEvent, before the commit, so a sign-up later rolled back
(a full team invite) had already been sent its welcome email.

**Endpoint.** `POST /signups` {email, name, inviteCode?} 201 (welcomeEmail PENDING); 409 already signed up or invite
full (rolled back); 422 unknown invite; 400 malformed. `GET /signups/{id}` with welcomeEmail PENDING, SENDING, SENT or
DEAD; 404. Simulated: emails are recorded in an in-memory mailbox, the CRM records a contact.

**Code.** SignupService saves, publishes SignedUp, then may join a team (which can fail). Listeners: two @Async
@TransactionalEventListener(AFTER_COMMIT): welcome email and CRM. WelcomeMailer claims the email (INSERT ... ON
CONFLICT DO NOTHING on sent_emails_once), retries 3 times with growing waits, then DEAD (the dead-letter state).
WelcomeEmail escapes the name (HtmlUtils) and strips line breaks from the subject; UTF-8.

**Database.** signups_email_unique (lower), signups_invite_fk, invites_seats_within_total, sent_emails_once,
_signup_fk, _status_known, _attempts_range, _dead_has_error.

**Tests.** EmailBeforeCommitTrapTest (old plain listener: no account, one email; new: nothing), SignupContractTest,
SlowCrmTest (CRM mocked to hang: 201 in under 2 s and the email still goes), WelcomeEmailMessagingTest (same event 5
times at once: one email; fails twice then recovers: SENT 3; never recovers: DEAD 3 and a late duplicate does not
resend), SignupDatabaseTest. Mutations: synchronous plain listener -> 2 red (the trap); @Async plain listener -> 1
(it ran before the commit, the claim failed on sent_emails_signup_fk, a valid sign-up got no email); CRM not async
-> 1; no claim -> 2; one attempt -> 2; no escaping -> 1.

**Practice.** 1: an analytics listener, no change to SignupService. 2: retry a dead-lettered email. Design: in-memory
events vs a transactional outbox.
