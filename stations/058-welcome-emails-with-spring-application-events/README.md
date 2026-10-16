# Station 058 · Welcome emails with Spring application events

Working Systems · 0–2 years · Core · SaaS · Types: Database, Messaging

Spring Boot 4.1.1 · Java 25 · ApplicationEventPublisher · @TransactionalEventListener(AFTER_COMMIT) · @Async on virtual threads · HtmlUtils · JdbcClient · PostgreSQL 17 · Flyway · Testcontainers · Awaitility. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** No email is sent and no CRM is called: the welcome email is recorded in an in-memory mailbox, and the CRM records the contact after a configurable delay. Sign-ups and invites are demo data, not Taskloom's.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 14 tests.

# 1 · Understand

## The problem in real life

1.  **Sign-up did everything**

    Taskloom's sign-up sent the welcome email, told the CRM and the analytics system, then answered. When the CRM was slow, sign-up was slow.

2.  **Events, too early**

    The team switched to events, with plain listeners. They run inside publishEvent, before the commit. Sign-ups rolled back later, for a full team invite, had already been welcomed by email.

3.  **The fix**

    Listeners that run after commit, on other threads; one welcome email per sign-up however often the event arrives; retries, then a dead-letter state; and a name escaped before it goes into HTML.

Side effects belong after the commit, and off the request's path.

## What are we building?

`POST /signups` saves a sign-up (optionally joining a team through an invite) and answers at once. After it commits, two things happen on their own: a welcome email and a CRM record. `GET /signups/{id}` shows where the welcome email is.

## An everyday analogy

A hotel front desk. The receptionist checks you in and hands over the key. Only then does someone else send the welcome note and update the loyalty system. If check-in is cancelled halfway, nobody sends the note; if the loyalty system is slow, you still get your key.

## How it works in 4 steps

1.  **The service saves** the sign-up and publishes `SignedUp`; nothing happens yet.
2.  **It may still fail** (a full invite): then everything rolls back, and the event is dropped.
3.  **On commit**, Spring hands the event to the after-commit listeners, each on its own thread.
4.  **The email listener** claims the email once, sends it, retries if the provider fails, and gives up to DEAD after three attempts.

Check yourself: the email listener runs after commit. Why must it still guard against duplicates?

Events can arrive twice: a retry by a person, a re-published event, a second instance. Without the claim row, each one sends an email. With it, the database lets exactly one through.

## What this station is not

- **No real email or CRM.** Both are simulated.
- **No outbox.** Events live in memory: a crash between commit and listener loses the email (see Production).
- **No login.** Sign-up is the start.

## Key terms

| Term                      | Simple meaning                                                         | Everyday example                                    | In this project               |
|---------------------------|------------------------------------------------------------------------|-----------------------------------------------------|-------------------------------|
| **Application event**     | A message one part of the app publishes and others listen to.          | A shop's bell that rings when a customer enters.    | `SignedUp`                    |
| **Plain listener**        | Runs at once, inside the publishing call, before the transaction ends. | Greeting the customer before they have paid.        | `@EventListener`              |
| **After-commit listener** | Runs only once the transaction has committed.                          | Sending the thank-you note after payment clears.    | `@TransactionalEventListener` |
| **Async**                 | Runs on another thread, so the caller does not wait.                   | Posting a letter instead of delivering it yourself. | `@Async`                      |
| **Retry and dead letter** | Try again a few times; then set the message aside for a person.        | Returned post kept at the counter.                  | `DEAD` status                 |
| **Escaping**              | Turning special characters into plain text so they cannot act as code. | Writing "\<b\>" instead of making text bold.        | `HtmlUtils.htmlEscape`        |

# 2 · Build: Spec

## Business problem

**Taskloom** (a fictional SaaS) welcomed people whose sign-up had failed, and made every sign-up wait for its slowest partner system.

## Acceptance criteria

1.  **Given** Asha signs up, **then** `201` with welcomeEmail PENDING, then one UTF-8 HTML welcome email, then SENT.
2.  **Given** Ravi signs up with a full invite, **then** `409`, no sign-up, and no email, ever.
3.  **Given** the CRM hangs, **then** the sign-up still answers in under 2 seconds and the email still goes.
4.  **Given** the same event five times at once, **then** one email.
5.  **Given** the provider fails twice, **then** the third attempt sends it; failing every time, the email is DEAD after 3 attempts, with the error.
6.  **Given** a name like `Zoë <b>& co</b>` or one with a line break, **then** it is text in the body and one line in the subject.
7.  **Given** a malformed body, `400`; a taken email, `409`; an unknown invite, `422`; an unknown sign-up, `404`.

## Requirements

- Side effects run after commit, never for a rolled-back sign-up.
- Slow partners never slow the sign-up.
- One welcome email per sign-up, guarded by the database.
- Bounded retries, then a visible dead-letter state.

## Learning objectives

- Publish and listen to application events.
- Choose between `@EventListener` and `@TransactionalEventListener`.
- Run listeners asynchronously, and test asynchronous code.
- Make a side effect idempotent, retried, and dead-lettered; and write safe HTML email.

# 2 · Build: API contract

## Endpoints

| Method | Path            | Purpose                                                             |
|--------|-----------------|---------------------------------------------------------------------|
| `POST` | `/signups`      | Sign up: `email`, `name`, optional `inviteCode` to join a team.     |
| `GET`  | `/signups/{id}` | The sign-up and its `welcomeEmail`: PENDING, SENDING, SENT or DEAD. |

## Status codes

| Status | When                                                             |
|--------|------------------------------------------------------------------|
| 201    | Signed up (the email follows after commit)                       |
| 200    | The sign-up                                                      |
| 400    | Malformed email, blank name, malformed invite code               |
| 404    | No such sign-up                                                  |
| 409    | Email already signed up; invite has no seats left (nothing kept) |
| 422    | Unknown invite (nothing kept)                                    |

## Captured examples

Captured with curl from the running app on 16 Oct 2026, in this order, against one fresh database (invite DESIGN-26 with seats, OPS-FULL without). JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Asha signs up

**Why:** `201` at once; the email is still PENDING.

Request

``` code
POST /signups HTTP/1.1
Content-Type: application/json

{
  "email": "asha@x.com",
  "name": "Asha Verma"
}
```

Response

``` code
HTTP/1.1 201 
Location: /signups/1
Content-Type: application/json

{
  "id": 1,
  "email": "asha@x.com",
  "name": "Asha Verma",
  "welcomeEmail": "PENDING"
}
```

### Case 2: a second later

**Why:** the after-commit listener has sent it: SENT.

Request

``` code
GET /signups/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 71

{
  "id": 1,
  "email": "asha@x.com",
  "name": "Asha Verma",
  "welcomeEmail": "SENT"
}
```

### Case 3: Ravi, invite OPS-FULL

**Why:** the sign-up was saved and the event published, then the invite failed: rolled back, `409`, no email.

Request

``` code
POST /signups HTTP/1.1
Content-Type: application/json

{
  "email": "ravi@x.com",
  "name": "Ravi Menon",
  "inviteCode": "OPS-FULL"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Invite OPS-FULL has no seats left.",
  "instance": "/signups",
  "status": 409,
  "title": "Invite full"
}
```

### Case 4: Meera, invite DESIGN-26

**Why:** a seat taken, `201`.

Request

``` code
POST /signups HTTP/1.1
Content-Type: application/json

{
  "email": "meera@x.com",
  "name": "Meera Nair",
  "inviteCode": "DESIGN-26"
}
```

Response

``` code
HTTP/1.1 201 
Location: /signups/3
Content-Type: application/json

{
  "id": 3,
  "email": "meera@x.com",
  "name": "Meera Nair",
  "welcomeEmail": "PENDING"
}
```

### Case 5: Asha@x.com again

**Why:** `409`.

Request

``` code
POST /signups HTTP/1.1
Content-Type: application/json

{
  "email": "Asha@x.com",
  "name": "Asha Verma"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "asha@x.com has already signed up.",
  "instance": "/signups",
  "status": 409,
  "title": "Already signed up"
}
```

### Case 6: asha.x.com

**Why:** `400`.

Request

``` code
POST /signups HTTP/1.1
Content-Type: application/json

{
  "email": "asha.x.com",
  "name": "Asha Verma"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/signups",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 7: sign-up 99

**Why:** `404`.

Request

``` code
GET /signups/99 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No sign-up 99.",
  "instance": "/signups/99",
  "status": 404,
  "title": "Sign-up not found"
}
```

## What happened after each commit

From the running app's log (`docs/captures/app-log.txt`) and the `sent_emails` table (`docs/captures/emails.txt`), after the requests above: two welcome emails, for Asha and Meera; none for Ravi, whose sign-up does not exist.

``` code
Welcome email for sign-up 1 sent on attempt 1 (simulated: recorded in the mailbox)
Welcome email for sign-up 3 sent on attempt 1 (simulated: recorded in the mailbox)
```

``` code
 id |    email    | status | attempts 
----+-------------+--------+----------
  1 | asha@x.com  | SENT   |        1
  3 | meera@x.com | SENT   |        1
(2 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                            | What happens                                   | Proved by                                                  |
|-------------------------------------------------|------------------------------------------------|------------------------------------------------------------|
| A sign-up                                       | `201` PENDING, then one email, then SENT       | `aSignupIsAnsweredAtOnceAndWelcomedAfter`                  |
| HTML and line breaks in the name                | Escaped in the body; one line in the subject   | `theNameIsTextInTheEmailNotHtmlOrHeaders`                  |
| An invite with seats                            | Seat taken, email sent                         | `anInviteWithSeatsJoinsTheTeam`                            |
| Full or unknown invite; taken email             | `409`, `422`, `409`; no email for any          | `aFullOrUnknownInviteOrATakenEmailIsRefusedAndNotWelcomed` |
| Malformed; unknown                              | `400`; `404`                                   | `malformedSignupsAre400`, `unknownSignupsAre404`           |
| A hanging CRM                                   | Sign-up and email unaffected                   | `theSignupAndTheEmailDoNotWaitForTheCrm`                   |
| The same event five times at once               | One email                                      | `theSameEventDeliveredFiveTimesAtOnceSendsOneEmail`        |
| Provider fails twice                            | Retried; sent on attempt 3                     | `aProviderThatFailsTwiceIsRetriedAndTheEmailGoesOnce`      |
| Provider never recovers                         | DEAD after 3; a late duplicate does not resend | `aProviderThatNeverRecoversLeavesTheEmailDeadForAPerson`   |
| Bad rows written directly; a rolled-back invite | Refused by named constraints; nothing kept     | `SignupDatabaseTest`                                       |

## The trap

Plausible but wrong

Sending email in a plain listener before commit; failed sign-ups still get mail.

The old flow is kept in the tests as `OldSignupFlow`, with the same steps as today and a plain `@EventListener` that sends the welcome email. Ravi signs up with a full invite: the exception rolls the sign-up back, there is no account, and the mailbox holds one "Welcome to Taskloom" addressed to him. Through today's API the same request leaves no sign-up and, checked for half a second, no email.

While building, each part was undone once. A synchronous plain listener, the old shape, turned 2 tests red: the trap and the full-invite contract test. An `@Async` plain listener turned a different one red. It ran on another thread before the commit, when PostgreSQL could not yet see the new sign-up, so its claim failed on `sent_emails_signup_fk` and a valid sign-up got no email. A CRM listener without `@Async` turned 1 red (the hanging-CRM test). Without the claim, 2; with one attempt instead of three, 2; without escaping, 1.

``` code
package com.taskloom.welcome;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: Ravi signs up with a full team invite, the old way and the new way. */
@Import({OldSignupFlow.class, OldSignupFlow.OldWelcomeListener.class})
class EmailBeforeCommitTrapTest extends ApiTest {

    @Autowired
    OldSignupFlow old;

    long signups() {
        return jdbc.sql("SELECT count(*) FROM signups").query(Long.class).single();
    }

    @Test
    void aPlainListenerSendsBeforeTheRollback() {
        assertThatThrownBy(() -> old.signUp("ravi@x.com", "Ravi Menon", "OPS-FULL")).hasMessage("invite full");
        assertThat(signups()).isZero();                                                // no account...
        assertThat(mailbox.all()).extracting(MailGateway.Message::to).containsExactly("ravi@x.com");   // ...but "welcome!"
    }

    @Test
    void anAfterCommitListenerSendsNothingForARolledBackSignup() throws Exception {
        signUp("ravi@x.com", "Ravi Menon", "OPS-FULL").andExpect(status().isConflict());
        assertThat(signups()).isZero();
        neverAnyMail();
    }
}
```

``` code
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
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                                           | Check with      |
|----------|-------------------------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below                    | `java -version` |
| Docker   | Docker Desktop (Windows, macOS) or Docker Engine (Linux), running | `docker info`   |
| Maven    | Not needed: the project ships the Maven wrapper                   |                 |

**macOS / Linux**

``` code
docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 14 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Virtual threads need JDK 21 or later.

## Try it yourself

Make the CRM slow and feel that sign-up does not care:

``` code
./mvnw spring-boot:run -Dspring-boot.run.arguments=--taskloom.crm.delay-ms=3000
curl -w "\n%{time_total}s\n" -X POST localhost:8080/signups -H "Content-Type: application/json" -d '{"email":"you@x.com","name":"You"}'
```

The answer comes back long before the CRM's three seconds. Then remove `@Async` from `registerInCrm` and try again.

## Troubleshooting

| You see                                  | Cause                                                         | Fix                                                               |
|------------------------------------------|---------------------------------------------------------------|-------------------------------------------------------------------|
| Emails for sign-ups that failed          | A plain `@EventListener`: it runs before the commit.          | `@TransactionalEventListener(phase = AFTER_COMMIT)`.              |
| An after-commit listener never runs      | The event was published outside a transaction.                | Publish inside one, or set `fallbackExecution = true` on purpose. |
| Sign-up slow when a partner is slow      | The listener runs on the request's thread.                    | `@Async` and `@EnableAsync`.                                      |
| Two welcome emails                       | The event arrived twice and nothing claimed it.               | Claim the email in the database first.                            |
| A foreign key error in an async listener | It ran before the commit and the new row was not visible yet. | After-commit, not a plain listener.                               |

## Project layout

``` tree
stations/058-welcome-emails-with-spring-application-events/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/taskloom/welcome/
│   ├── SignupController.java   ├── SignupService.java   ├── SignedUp.java   ├── Listeners.java
│   ├── WelcomeMailer.java   ├── WelcomeEmail.java   ├── MailGateway.java   ├── Mailbox.java
│   ├── CrmClient.java   └── WelcomeApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__signups_invites_emails.sql, V2__demo_invites.sql
├── src/test/java/com/taskloom/welcome/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then what happens after the commit.

#### `src/main/java/com/taskloom/welcome/SignupController.java`

Does  
Validates and normalises the sign-up; reads it back with its email status.

Why  
HTTP only.

Without it  
Side effects started from the controller.

#### `src/main/java/com/taskloom/welcome/SignupService.java`

Does  
Saves the sign-up, publishes `SignedUp`, joins the team.

Why  
Knows no email, CRM or analytics.

Without it  
A sign-up that waits for partners.

#### `src/main/java/com/taskloom/welcome/Listeners.java`

Does  
The welcome email and the CRM, each `@Async` and after commit.

Why  
Rolled-back sign-ups cause nothing; slow partners slow nothing.

Without it  
Mail for sign-ups that do not exist.

- `@TransactionalEventListener(phase = AFTER_COMMIT)` holds the event until the commit, and drops it on rollback.
- `@Async` hands it to Spring's executor (virtual threads here).

#### `src/main/java/com/taskloom/welcome/WelcomeMailer.java`

Does  
Claims, sends, retries, dead-letters.

Why  
The database decides that one email goes out.

Without it  
Duplicates and silent losses.

- The claim is `INSERT ... ON CONFLICT DO NOTHING`: zero rows means someone already has it.
- Waits grow with each attempt; after the last, DEAD with the error.

#### `src/main/java/com/taskloom/welcome/WelcomeEmail.java`

Does  
The HTML template, UTF-8.

Why  
User input escaped in the body, line breaks removed from the subject.

Without it  
HTML or header injection through a name.

#### `src/main/java/com/taskloom/welcome/Mailbox.java`

The simulated provider: records each message.

#### `src/main/java/com/taskloom/welcome/MailGateway.java`

The one-method interface the mailer depends on.

#### `src/main/java/com/taskloom/welcome/CrmClient.java`

The simulated CRM, with a configurable delay.

#### `src/main/java/com/taskloom/welcome/SignedUp.java`

The event.

#### `src/main/resources/db/migration/V1__signups_invites_emails.sql`

Sign-ups, invites and the email claim table, with named constraints.

#### `src/main/resources/db/migration/V2__demo_invites.sql`

One invite with seats, one full.

#### `src/main/resources/application.yaml`

Virtual threads for `@Async`; retry attempts and waits; the CRM's delay.

#### `src/main/java/com/taskloom/welcome/WelcomeApplication.java`

Entry point; `@EnableAsync`.

# 2 · Build: Tests

## Required tests for this station

| Required by             | Requirement                                           | Test class                      | Result |
|-------------------------|-------------------------------------------------------|---------------------------------|--------|
| Every station           | HTTP contract: valid, invalid, not found              | `SignupContractTest` (6)        | pass   |
| Every station           | Reproduce the failure before the fix                  | `EmailBeforeCommitTrapTest` (2) | pass   |
| Database                | Rollback and constraint tests against a real database | `SignupDatabaseTest` (2)        | pass   |
| Messaging               | Duplicate-delivery, retry and dead-letter tests       | `WelcomeEmailMessagingTest` (3) | pass   |
| This station's concepts | Async listeners: a hanging CRM                        | `SlowCrmTest` (1)               | pass   |

## Testing asynchronous code

Async results arrive later, so the tests wait for them with Awaitility, up to 5 seconds, instead of sleeping a fixed time. "Never" is checked by watching for half a second that nothing arrives. The hanging CRM is a Mockito mock that blocks on a latch, released by the test.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.welcome.SlowCrmTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.welcome.SignupContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.welcome.EmailBeforeCommitTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.welcome.WelcomeEmailMessagingTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.welcome.SignupDatabaseTest
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/taskloom/welcome/EmailBeforeCommitTrapTest.java`

Written first: the old plain listener and today's after-commit one, for the same failed sign-up.

#### `src/test/java/com/taskloom/welcome/SignupContractTest.java`

Sign-ups, invites, the email that follows, escaping, and every refusal.

#### `src/test/java/com/taskloom/welcome/WelcomeEmailMessagingTest.java`

Duplicate events, a provider that recovers, and one that never does.

#### `src/test/java/com/taskloom/welcome/SlowCrmTest.java`

A CRM that hangs, mocked with a latch.

#### `src/test/java/com/taskloom/welcome/SignupDatabaseTest.java`

Named constraints and a rolled-back sign-up.

#### `src/test/java/com/taskloom/welcome/OldSignupFlow.java`

The old flow and its plain listener, kept only in tests.

#### `src/test/java/com/taskloom/welcome/ApiTest.java`

Shared setup, Awaitility helpers, parallel calls.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/taskloom/welcome/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=AnalyticsChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 14 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in (Java files and one migration), all 16 tests pass (14 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## An analytics listener

Record every committed sign-up in a new `analytics_events` table, from a third after-commit listener, without changing `SignupService`.

**Done when:** the test in `AnalyticsChallengeTest` passes.

Hints

- A new method in `Listeners`, and a migration.
- The rolled-back sign-up in the test must leave no row.

#### `challenge/AnalyticsChallengeTest.java`

``` code
package com.taskloom.welcome;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: a third after-commit listener records every committed sign-up in analytics_events (a new migration),
 * without a line changed in SignupService. A rolled-back sign-up records nothing.
 */
class AnalyticsChallengeTest extends ApiTest {

    long analytics() {
        return jdbc.sql("SELECT count(*) FROM analytics_events WHERE name = 'signed_up'").query(Long.class).single();
    }

    @Test
    void onlyCommittedSignupsAreCounted() throws Exception {
        jdbc.sql("DELETE FROM analytics_events").update();
        signUp("asha@x.com", "Asha Verma", null).andExpect(status().isCreated());
        signUp("ravi@x.com", "Ravi Menon", "OPS-FULL").andExpect(status().isConflict());
        eventually(() -> assertThat(analytics()).isEqualTo(1));
        Thread.sleep(300);
        assertThat(analytics()).isEqualTo(1);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 25 minutes

## Send a dead email again

Add `POST /signups/{id}/welcome-email/retry`: a DEAD email goes back to SENDING and is retried as before. Not DEAD: `409`; unknown: `404`.

**Done when:** the test in `ResendChallengeTest` passes.

Hints

- Move DEAD to SENDING with a conditional UPDATE: zero rows means it was not dead.
- Reuse the delivery loop; only the claim differs.

#### `challenge/ResendChallengeTest.java`

``` code
package com.taskloom.welcome;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doCallRealMethod;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /signups/{id}/welcome-email/retry takes a DEAD email out of the dead-letter state and tries again,
 * with the same retries, answering the sign-up with its new status. Not DEAD: 409. Unknown sign-up: 404.
 */
class ResendChallengeTest extends ApiTest {

    @MockitoSpyBean
    Mailbox provider;

    @Test
    void aPersonCanSendADeadEmailAgain() throws Exception {
        doThrow(new IllegalStateException("550 mailbox unavailable")).when(provider).send(any());
        signUp("asha@x.com", "Asha Verma", null).andExpect(status().isCreated());
        eventually(() -> assertThat(welcomeStatus(1)).isEqualTo("DEAD"));

        doCallRealMethod().when(provider).send(any());   // the provider is back
        mvc.perform(post("/signups/1/welcome-email/retry")).andExpect(status().isOk()).andExpect(jsonPath("$.welcomeEmail").value("SENT"));
        assertThat(mailbox.all()).hasSize(1);
        mvc.perform(post("/signups/1/welcome-email/retry")).andExpect(status().isConflict());
        mvc.perform(post("/signups/99/welcome-email/retry")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Events in memory, or an outbox?

If the app restarts a millisecond after a sign-up commits, the in-memory event is gone and the welcome email never goes. Sketch a transactional outbox: a table written in the sign-up's transaction, and a poller that sends. What does it cost, and which of this station's tests would change?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test with the old plain listener as a real bean.
2.  Publish one event from the service; move each side effect into its own after-commit, async listener.
3.  Make the email idempotent with a claim row; add bounded retries and a dead-letter state.
4.  Escape user input in the template; test asynchronous outcomes by waiting for them.

## Design alternatives and trade-offs

| Approach                                       | What it costs                                                 | Verdict         |
|------------------------------------------------|---------------------------------------------------------------|-----------------|
| After-commit, async listeners with a claim row | Events in memory: lost if the app dies after commit.          | Chosen          |
| Plain `@EventListener`                         | Runs before commit: mail for failed sign-ups.                 | The trap        |
| Calling email and CRM directly in the service  | Every partner's speed and failure becomes the sign-up's.      | The old code    |
| Transactional outbox + poller                  | A table and a job; nothing lost on a crash.                   | The next step   |
| A message broker (Kafka, RabbitMQ)             | Durable and shareable across services; another system to run. | Across services |

## Database design

| Table         | Constraints                                                                                                                                                                 |
|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `signups`     | `signups_email_unique` (on `lower(email)`), `signups_invite_fk`                                                                                                             |
| `invites`     | `invites_seats_within_total`                                                                                                                                                |
| `sent_emails` | `sent_emails_once` (primary key: one per sign-up and kind), `sent_emails_signup_fk`, `sent_emails_status_known`, `sent_emails_attempts_range`, `sent_emails_dead_has_error` |

``` code
-- Taskloom sign-ups, team invites, and one row per email the system has taken on.
CREATE TABLE invites (
    code        VARCHAR(20) PRIMARY KEY,
    team_name   VARCHAR(80) NOT NULL,
    seats_used  INT         NOT NULL DEFAULT 0,
    seats_total INT         NOT NULL,
    CONSTRAINT invites_seats_within_total CHECK (seats_used BETWEEN 0 AND seats_total)
);

CREATE TABLE signups (
    id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    email       VARCHAR(254) NOT NULL,
    name        VARCHAR(80)  NOT NULL,
    invite_code VARCHAR(20),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT signups_invite_fk FOREIGN KEY (invite_code) REFERENCES invites (code)
);
CREATE UNIQUE INDEX signups_email_unique ON signups (lower(email));

-- The claim, the outcome and the dead-letter state of each email in one row. The primary key is the guard against
-- sending the same email twice.
CREATE TABLE sent_emails (
    signup_id  BIGINT       NOT NULL,
    kind       VARCHAR(20)  NOT NULL,
    status     VARCHAR(10)  NOT NULL,
    attempts   INT          NOT NULL DEFAULT 0,
    last_error VARCHAR(200),
    CONSTRAINT sent_emails_once PRIMARY KEY (signup_id, kind),
    CONSTRAINT sent_emails_signup_fk FOREIGN KEY (signup_id) REFERENCES signups (id),
    CONSTRAINT sent_emails_status_known CHECK (status IN ('SENDING', 'SENT', 'DEAD')),
    CONSTRAINT sent_emails_attempts_range CHECK (attempts BETWEEN 0 AND 10),
    CONSTRAINT sent_emails_dead_has_error CHECK (status <> 'DEAD' OR last_error IS NOT NULL)
);
```

# 3 · Go deeper: Production

The crash window  
Between commit and listener the event lives only in memory. A restart there loses the email. A nightly query for sign-ups with no `sent_emails` row finds them; an outbox removes the window.

Watch the dead letters  
DEAD emails need a person. Alert when their count grows, and give support a way to send again (challenge 2).

Shutdown  
Async tasks still running at shutdown are cut off. Spring's executor can wait for them (`spring.task.execution.shutdown.await-termination`).

Email deliverability  
A real provider needs a verified sending domain (SPF, DKIM, DMARC) and a plain-text part next to the HTML.

# 3 · Go deeper: Interview

## Interview takeaways

@EventListener vs @TransactionalEventListener?

@EventListener runs immediately, inside publishEvent, in the publisher's transaction. @TransactionalEventListener waits for a transaction phase, by default AFTER_COMMIT, and is skipped if the transaction rolls back.

Why make the listener @Async?

So its work, and any slowness or failure in it, does not delay the request. The trade-off: errors no longer reach the caller, so they must be recorded somewhere.

How do you stop duplicate emails?

Claim the email in the database before sending: a unique key on (sign-up, kind) and INSERT ... ON CONFLICT DO NOTHING. Only the caller that inserted the row sends.

What is a dead letter?

A message that failed every allowed attempt, set aside with its error for a person, instead of being retried forever or dropped.

Why escape a name in an email?

It is user input placed into HTML. Unescaped, "\<script\>" or "\<a href\>" becomes markup in the email; a line break in a subject header can add headers.

## Self-check rubric

| Area        | Meets the bar                 | Above the bar                                                |
|-------------|-------------------------------|--------------------------------------------------------------|
| Correctness | All 14 tests pass.            | You swapped in a plain listener and explained both failures. |
| Events      | After-commit and async.       | You know the crash window and the outbox.                    |
| Delivery    | Once, retried, dead-lettered. | Support can resend a dead email.                             |
| Email       | Escaped, UTF-8.               | Subject header injection covered.                            |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any side effect:

- Can it happen for a transaction that later rolls back?
- Does the request wait for it?
- What happens if it runs twice, or fails every time?
- Is user input escaped for where it ends up (HTML, headers, SQL)?
