# Station 072 · Password reset by email

Working Systems · 0–2 years · Core · Recruitment · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · Spring Security 7 · SecureRandom tokens, stored as SHA-256 · single-use UPDATE … RETURNING · JdbcClient · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Email is simulated: a row is written to an outbox table and nothing is sent. Candidates are demo data, not Hireloop's.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 17 tests.

# 1 · Understand

## The problem in real life

1.  **Forgot my password**

    A candidate asks for a reset link. The old system stored the link's token as plain text, with no expiry, and never marked it used.

2.  **Keys left lying around**

    Old emails in an inbox stayed keys to the account for ever, and anyone who read the reset table could take over any account. The form also said "No account found with this email", so attackers could test which emails were registered.

3.  **The fix**

    One reply for every email. Links are 256 random bits, kept only as a hash, valid for 30 minutes, usable once, and all cancelled when the password changes.

A reset link is a password. Treat it like one: short-lived, single-use, and never stored in the clear.

## What are we building?

`POST /password-resets` sends a link (if the account exists, and never says whether it does); `POST /password-resets/{token}/complete` uses the link once to set a new password.

## An everyday analogy

A hotel front desk that hands out a one-time key card, valid for half an hour, only to the guest's registered email, and answers "if you are staying with us, we have sent it" to anyone who asks.

## How it works in 4 steps

1.  **Request**: if an active account has the email, make a random token, store only its hash, and write an email with the link.
2.  **Reply** the same way in every case.
3.  **Use the link**: one database statement checks it is unused and unexpired and marks it used.
4.  **Set the password** and cancel every other open link of the account.

Check yourself: why is a plain SHA-256 fine for reset tokens but not for passwords?

A token is 256 random bits made by the server: there is no list of likely tokens to try, so a fast hash loses nothing. Passwords are chosen by people, and lists of likely ones exist, so they need a slow, salted hash (station 071).

## What this station is not

- **No email is sent.** The outbox row is the simulated email.
- **No sign-in sessions.** Ending other sessions after a reset is Practice 3, on paper.
- **No CAPTCHA.** A per-account limit stops flooding one inbox; abuse from many sources needs more.

## Key terms

| Term                    | Simple meaning                                                                  | Everyday example                                                   | In this project            |
|-------------------------|---------------------------------------------------------------------------------|--------------------------------------------------------------------|----------------------------|
| **Reset link**          | A one-time key, sent by email, that lets its holder choose a new password.      | A spare key left with a neighbour, for one use.                    | `…/reset-password?token=…` |
| **Single use**          | The link stops working once it has been used.                                   | A ticket torn at the gate.                                         | `used_at`                  |
| **Expiry**              | The link stops working after a while, used or not.                              | A parking ticket valid for 30 minutes.                             | `expires_at`, 30 minutes   |
| **Account enumeration** | Finding out which emails have accounts from how a form replies.                 | A receptionist who says "no such guest" or "I'll ring their room". | one reply for every email  |
| **Token hash**          | Only a fingerprint of the link is stored, so a copy of the table opens nothing. | The hotel keeps a key's serial number, not a spare key.            | `token_hash`               |
| **Outbox**              | Emails written as rows for a sender to pick up; here nobody sends them.         | A post tray.                                                       | `outbox_emails`            |

# 2 · Build: Spec

## Business problem

**Hireloop** (a fictional job portal): reset links never expire, can be used twice, and the form tells attackers which emails have accounts.

## Acceptance criteria

Demo data: Priya and Arjun are active, Kiran is suspended. Tests control the clock.

1.  **Given** any email, known or not, **then** `202` with the same message; only an active account gets an email.
2.  **Given** the link and a new password, **then** `204`; the old password stops working, the new one works.
3.  **Given** the same link again, or after 30 minutes, or a link nobody issued, **then** the same `400`.
4.  **Given** two open links and one used, **then** the other no longer works.
5.  **Given** ten requests for one email, **then** at most three links are sent.
6.  **Given** one link sent ten times at the same moment, **then** exactly one succeeds.

## Requirements

- Tokens come from `SecureRandom` (256 bits); only their SHA-256 is stored.
- A link is valid for 30 minutes and once; the database refuses longer windows.
- No reply, status or timing difference that depends on whether an account exists, as far as the code can control.
- A password change cancels every open link of the account.

## Learning objectives

- Design single-use, expiring tokens, and store them safely.
- Avoid account enumeration in replies.
- Make "use once" safe under concurrency with one conditional update.
- Test time-based rules with a controllable clock.

# 2 · Build: API contract

## Endpoints

| Method | Path                                | Purpose                                                             |
|--------|-------------------------------------|---------------------------------------------------------------------|
| `POST` | `/password-resets`                  | `{email}`; always `202` with one message.                           |
| `POST` | `/password-resets/{token}/complete` | `{newPassword}`; `204` once per link.                               |
| `GET`  | `/candidates/me`                    | The signed-in candidate (HTTP Basic), to see the new password work. |

## Status codes

| Status    | When                                                                                                                           |
|-----------|--------------------------------------------------------------------------------------------------------------------------------|
| 202       | Every reset request with a well-formed email                                                                                   |
| 204       | The new password is set                                                                                                        |
| 400       | Not an email; a new password under 12 or over 64 characters or 72 bytes; a link that is unknown, used or expired (one message) |
| 401 / 403 | Profile without valid credentials / for a suspended account                                                                    |

## Captured examples

Captured with curl from the running app on 19 Oct 2026. The token is replaced by a placeholder in every capture: a real one is a key to an account. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: a known email

**Why:** `202` and a link in the outbox.

Request

``` code
POST /password-resets HTTP/1.1
Content-Type: application/json

{
  "email": "priya@example.com"
}
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json
Content-Length: 93

{
  "message": "If an account exists for this email, we have sent a link to reset its password."
}
```

### Case 2: an unknown email

**Why:** exactly the same reply; no email.

Request

``` code
POST /password-resets HTTP/1.1
Content-Type: application/json

{
  "email": "nobody@example.com"
}
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json
Content-Length: 93

{
  "message": "If an account exists for this email, we have sent a link to reset its password."
}
```

### Case 3: the link from the email

**Why:** `204`: the password is changed.

Request

``` code
POST /password-resets/<token from the email>/complete HTTP/1.1
Content-Type: application/json

{
  "newPassword": "priya-new-long-password"
}
```

Response

``` code
HTTP/1.1 204
```

### Case 4: the same link again

**Why:** used: the one "invalid or expired" message.

Request

``` code
POST /password-resets/<token from the email>/complete HTTP/1.1
Content-Type: application/json

{
  "newPassword": "someone-elses-password"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "This link is invalid or has expired; ask for a new one",
  "instance": "/password-resets/<token from the email>/complete",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: the new password

**Why:** it works.

Request

``` code
GET /candidates/me HTTP/1.1
Authorization: Basic cHJpeWFAZXhhbXBsZS5jb206cHJpeWEtbmV3LWxvbmctcGFzc3dvcmQ=
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 60

{
  "id": 1,
  "email": "priya@example.com",
  "fullName": "Priya Nair"
}
```

### Case 6: a suspended account

**Why:** `403`.

Request

``` code
GET /candidates/me HTTP/1.1
Authorization: Basic a2lyYW5AZXhhbXBsZS5jb206a2lyYW4tb2xkLXBhc3N3b3Jk
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 104

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This account cannot do this.",
  "instance": "/candidates/me"
}
```

## What was stored

From `psql` in `docs/capture.sh`: the outbox (with the token masked), and the reset row before and after it was used.

``` code
     to_email      |           subject            |                                                  body                                                  
-------------------+------------------------------+--------------------------------------------------------------------------------------------------------
 priya@example.com | Reset your Hireloop password | Someone asked to reset the password for this account. If it was you, open this link within 30 minutes:+
                   |                              | https://app.hireloop.example/reset-password?token=<43 random characters>                              +
                   |                              | If it was not you, ignore this email.
(1 row)
```

``` code
                            token_hash                            | valid_for | used 
------------------------------------------------------------------+-----------+------
 725ea7036e3aa694cdba1c042fb3a1653eb94c0cc265ebe9c7cfd86e766a5864 | 00:30:00  | f
(1 row)
```

``` code
                            token_hash                            | used 
------------------------------------------------------------------+------
 725ea7036e3aa694cdba1c042fb3a1653eb94c0cc265ebe9c7cfd86e766a5864 | t
(1 row)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                      | What happens                    | Proved by                                  |
|-----------------------------------------------------------|---------------------------------|--------------------------------------------|
| The whole reset                                           | Old password out, new one in    | `theWholeResetFromRequestToNewPassword`    |
| An unknown email                                          | Same reply, no email            | `anUnknownEmailGetsTheSameReplyAndNoEmail` |
| A link nobody issued                                      | `400`                           | `anUnknownLinkIs400`                       |
| Bad email, short or too-long password                     | `400`, and the link still works | `badRequestsAre400`                        |
| Suspended account                                         | `403` on the profile, no link   | `aSuspendedAccountIs403AndGetsNoLink`      |
| A link for one account                                    | Changes only that account       | `aLinkChangesOnlyTheAccountItWasSentFor`   |
| Two open links, one used                                  | The other is cancelled          | `aNewPasswordCancelsEveryOtherOpenLink`    |
| Ten requests                                              | Three links                     | `floodingTheFormSendsAtMostThreeLinks`     |
| Quotes, a 500-character token, path tricks                | The same `400`                  | `oddTokensAreJustUnknownLinks`             |
| One link, ten requests at once                            | Exactly one `204`               | `oneLinkUsedTwiceAtTheSameMomentWorksOnce` |
| Plain tokens, month-long links, late use written directly | Refused by named constraints    | `ResetDatabaseTest`                        |

## The trap

Plausible but wrong

Reusable, non-expiring tokens and different replies for known and unknown emails.

The old reset is kept in the test as plain SQL against an `old_reset_tokens` table:

- **Two replies.** "We have sent you a reset link" or "No account found with this email": anyone can test a list of emails. The new replies are byte for byte the same.
- **A key for ever.** The old token sits in its table as text, and 31 days later it still works. The new link fails after 30 minutes and after one use, and the table holds only its SHA-256.

While building, each fix was undone once: a different reply for unknown emails turned 3 tests red; a reusable link 2 (including the parallel test); no expiry check 1; keeping the other open links 1; no flood limit 1; storing the token itself instead of its hash 9, because the database's shape CHECK then refused every link.

``` code
package com.hireloop.resets;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old reset, kept here as plain SQL: a token stored as text, with no expiry and no "used" mark,
 * and a request form that said whether the email had an account. Then the same steps against the new endpoints.
 */
class ReusableTokenTrapTest extends ApiTest {

    @BeforeEach
    void oldTable() {
        jdbc.sql("CREATE TABLE old_reset_tokens (email VARCHAR(254), token VARCHAR(36))").update();
    }

    @AfterEach
    void dropOldTable() {
        jdbc.sql("DROP TABLE old_reset_tokens").update();
    }

    /** The old form's reply. */
    private String oldRequest(String email) {
        boolean exists = jdbc.sql("SELECT count(*) FROM candidates WHERE email = ?").param(email).query(Long.class).single() > 0;
        if (!exists) {
            return "No account found with this email";
        }
        jdbc.sql("INSERT INTO old_reset_tokens VALUES (?, ?)").params(email, UUID.randomUUID().toString()).update();
        return "We have sent you a reset link";
    }

    /** The old link check: does this token exist? Nothing else. */
    private boolean oldTokenWorks(String token) {
        return jdbc.sql("SELECT count(*) FROM old_reset_tokens WHERE token = ?").param(token).query(Long.class).single() > 0;
    }

    @Test
    void theOldFormToldAttackersWhichEmailsHaveAccounts() throws Exception {
        assertThat(oldRequest("priya@example.com")).isNotEqualTo(oldRequest("nobody@example.com"));
        String known = requestReset("priya@example.com").andReturn().getResponse().getContentAsString();
        String unknown = requestReset("nobody@example.com").andReturn().getResponse().getContentAsString();
        assertThat(known).isEqualTo(unknown);
    }

    @Test
    void anOldLinkWorkedTwiceAndForever() throws Exception {
        oldRequest("priya@example.com");
        String token = jdbc.sql("SELECT token FROM old_reset_tokens").query(String.class).single();   // and anyone reading the table can use it
        assertThat(oldTokenWorks(token)).isTrue();
        later(Duration.ofDays(31));
        assertThat(oldTokenWorks(token)).isTrue();   // a month later, still a key to the account
    }

    @Test
    void aNewLinkWorksOnceAndOnlyFor30Minutes() throws Exception {
        requestReset("priya@example.com");
        String token = linkTokenFor("priya@example.com");
        complete(token, "first-new-password").andExpect(status().isNoContent());
        complete(token, "second-new-password").andExpect(status().isBadRequest());   // used: the same answer as unknown

        requestReset("arjun@example.com");
        later(Duration.ofMinutes(31));
        complete(linkTokenFor("arjun@example.com"), "too-late-password").andExpect(status().isBadRequest());
        me("arjun@example.com", "arjun-old-password").andExpect(status().isOk());
    }

    @Test
    void theTableHoldsOnlyAHashOfTheLink() throws Exception {
        requestReset("priya@example.com");
        String token = linkTokenFor("priya@example.com");
        assertThat(jdbc.sql("SELECT count(*) FROM password_resets WHERE token_hash = ?").param(token).query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT token_hash FROM password_resets").query(String.class).single()).isEqualTo(PasswordResets.sha256(token));
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
./mvnw test                 # all 17 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask for a link, read the simulated email, and use the link:

``` code
curl -X POST http://localhost:8080/password-resets -H 'Content-Type: application/json' -d '{"email": "arjun@example.com"}'
docker compose exec postgres psql -U hireloop -d hireloop -c "SELECT body FROM outbox_emails ORDER BY id DESC LIMIT 1"
curl -X POST "http://localhost:8080/password-resets/<token>/complete" -H 'Content-Type: application/json' -d '{"newPassword": "arjun-new-long-password"}'
```

Run the last command twice: the second answer is the same as for a made-up token.

## Troubleshooting

| You see                                 | Cause                                                           | Fix                                                                              |
|-----------------------------------------|-----------------------------------------------------------------|----------------------------------------------------------------------------------|
| `403` on a new endpoint                 | The filter chain ends in `denyAll`: unlisted paths are refused. | Add a rule for the path. Found while building this station's Practice.           |
| `password_resets_used_in_time` violated | A link marked used after its expiry.                            | Use it with the conditional `UPDATE`, which checks expiry in the same statement. |
| The link works in tests but not by hand | The tests' clock is fixed; the app's is real.                   | Use the link within 30 minutes.                                                  |
| Links in logs or analytics              | Reset URLs logged by a proxy or a page tracker.                 | Keep the token out of logs; use it as soon as the page opens.                    |

## Project layout

``` tree
stations/072-password-reset-by-email/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/hireloop/resets/
│   ├── ResetController.java   ├── PasswordResets.java   ├── SecurityConfig.java
│   ├── CandidateAccounts.java   ├── ProblemResponses.java   └── ResetsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__candidates_and_resets.sql, V2__demo_candidates.sql
├── src/test/java/com/hireloop/resets/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/hireloop/resets/ResetController.java`

Does  
The two reset steps and the profile.

Why  
One constant reply for every request; the new password's length and bytes checked.

Without it  
A friendly "no such account" that answers attackers too.

#### `src/main/java/com/hireloop/resets/PasswordResets.java`

Does  
Makes, stores and uses reset links.

Why  
`SecureRandom` tokens, only their hash stored, one conditional `UPDATE … RETURNING` to use a link, every other link cancelled.

Without it  
Links that work twice, work for ever, or open accounts for whoever reads the table.

- The unknown-email path returns early: no email and no error. Its timing is close to, not equal to, the known path; a constant-time design would hand both to a queue.
- Unknown, used and expired links share one message.

#### `src/main/java/com/hireloop/resets/SecurityConfig.java`

Does  
Both reset steps open, the profile for active candidates, everything else denied.

Why  
The reset is for people who cannot sign in.

Without it  
A new endpoint quietly open: with `denyAll` last, a forgotten rule fails closed.

#### `src/main/java/com/hireloop/resets/CandidateAccounts.java`

Sign-in by email; suspended accounts get a role that the profile refuses.

#### `src/main/java/com/hireloop/resets/ProblemResponses.java`

401 and 403 as problem JSON.

#### `src/main/resources/db/migration/V1__candidates_and_resets.sql`

Does  
Candidates, reset links and the outbox, with named constraints.

Why  
The database refuses plain tokens, links longer than an hour, and use after expiry.

Without it  
Rules that only the Java code knows.

#### `src/main/resources/db/migration/V2__demo_candidates.sql`

Three candidates, with bcrypt hashes made by pgcrypto.

#### `src/main/resources/application.yaml`

The link address and its 30 minutes.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/hireloop/resets/ResetsApplication.java`

Entry point and the clock.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                  | Result |
|---------------|-------------------------------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `ResetContractTest` (4)     | pass   |
| Every station | Reproduce the failure before the fix                              | `ReusableTokenTrapTest` (4) | pass   |
| Database      | Rollback and constraint tests against a real database             | `ResetDatabaseTest` (2)     | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `ResetSecurityTest` (7)     | pass   |

Time-based rules use a test clock that the tests move forward: "31 minutes later" takes no time to test. The parallel test sends one link ten times on virtual threads released by one latch.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.hireloop.resets.ResetContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.hireloop.resets.ReusableTokenTrapTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.hireloop.resets.ResetDatabaseTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.hireloop.resets.ResetSecurityTest
[INFO] Tests run: 17, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/hireloop/resets/ReusableTokenTrapTest.java`

Written first: the old two replies and the eternal token, then the new link's limits.

#### `src/test/java/com/hireloop/resets/ResetSecurityTest.java`

401, 403, one account only, cancelled links, flooding, odd tokens, and a parallel use.

#### `src/test/java/com/hireloop/resets/ResetDatabaseTest.java`

The reset table's constraints with plain SQL, and a rolled-back half reset.

#### `src/test/java/com/hireloop/resets/ResetContractTest.java`

The flow through HTTP.

#### `src/test/java/com/hireloop/resets/ApiTest.java`

Shared setup: the movable clock, demo candidates, and reading the link from the outbox.

#### `src/test/java/com/hireloop/resets/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/hireloop/resets/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ChangedNoticeChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 17 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 20 tests pass (17 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 15 minutes

## Tell the owner

After a reset, write a second email: "Your Hireloop password was changed", with no link in it.

**Done when:** the test in `ChangedNoticeChallengeTest` passes.

Hints

- Write it in the same transaction as the change, so a failed change sends no notice.

#### `challenge/ChangedNoticeChallengeTest.java`

``` code
package com.hireloop.resets;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: after a reset, a second email tells the owner "Your Hireloop password was changed", so someone who
 * did not ask for it notices at once. The notice contains no link.
 */
class ChangedNoticeChallengeTest extends ApiTest {

    @Test
    void theOwnerIsToldTheirPasswordChanged() throws Exception {
        requestReset("priya@example.com");
        complete(linkTokenFor("priya@example.com"), "priya-new-long-password");
        assertThat(jdbc.sql("SELECT subject FROM outbox_emails WHERE to_email = 'priya@example.com' ORDER BY id").query(String.class).list())
                .containsExactly("Reset your Hireloop password", "Your Hireloop password was changed");
        assertThat(jdbc.sql("SELECT body FROM outbox_emails WHERE subject = 'Your Hireloop password was changed'").query(String.class).single())
                .doesNotContain("token=");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Every password change cancels links

Add `PUT /candidates/me/password` `{currentPassword, newPassword}` for signed-in candidates. It must also cancel open reset links.

**Done when:** both tests in `ChangePasswordCancelsLinksChallengeTest` pass.

Hints

- Move "set the password, cancel links, notify" into one method both paths call.
- Found while building: the new path got `403` until the filter chain listed it, because the chain ends in `denyAll`.

#### `challenge/ChangePasswordCancelsLinksChallengeTest.java`

``` code
package com.hireloop.resets;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: PUT /candidates/me/password {currentPassword, newPassword} (signed in) changes the password: 204, 422
 * for a wrong current password. Like a reset, it cancels every open reset link of the account.
 */
class ChangePasswordCancelsLinksChallengeTest extends ApiTest {

    @Test
    void changingThePasswordKillsWaitingLinks() throws Exception {
        requestReset("arjun@example.com");
        String waiting = linkTokenFor("arjun@example.com");
        mvc.perform(put("/candidates/me/password").with(httpBasic("arjun@example.com", "arjun-old-password")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"currentPassword\":\"arjun-old-password\",\"newPassword\":\"arjun-new-long-password\"}")).andExpect(status().isNoContent());
        complete(waiting, "attacker-chosen-password").andExpect(status().isBadRequest());
        me("arjun@example.com", "arjun-new-long-password").andExpect(status().isOk());
    }

    @Test
    void theCurrentPasswordMustBeRight() throws Exception {
        mvc.perform(put("/candidates/me/password").with(httpBasic("arjun@example.com", "arjun-old-password")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"currentPassword\":\"a-wrong-password\",\"newPassword\":\"arjun-new-long-password\"}")).andExpect(status().isUnprocessableContent());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## What else should a reset end?

With sessions or tokens (stations 073 and 074), an attacker who already signed in keeps that session after the owner resets the password. Design how a reset ends every other session: a `password_changed_at` compared with each token's issue time, a per-account token version, or deleting refresh tokens. Which works for tokens that are checked without a database?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old replies and the eternal, plain-text token.
2.  Make tokens random and long, keep only their hash, and give them an expiry.
3.  Use a link with one conditional `UPDATE … RETURNING`, so "once" holds under concurrency.
4.  Answer every request the same way, and limit links per account.

## Design alternatives and trade-offs

| Approach                                              | What it costs                                                    | Verdict                    |
|-------------------------------------------------------|------------------------------------------------------------------|----------------------------|
| Random token, hash stored, 30 minutes, single use     | A table and a cleanup job for old rows.                          | Chosen                     |
| Token stored as text, no expiry                       | Old emails and table copies are keys.                            | The trap                   |
| A signed token (HMAC or JWT) with an expiry, no table | No storage; cannot be made single-use without storing something. | Not single-use             |
| A 6-digit code instead of a link                      | Easy to type; must be rate-limited hard, 10⁶ guesses is small.   | With strict attempt limits |
| Check-then-update in two statements                   | Two parallel uses can both pass.                                 | Race                       |

## Database design

| Object                                        | What                                         | Why                                       |
|-----------------------------------------------|----------------------------------------------|-------------------------------------------|
| `password_resets_token_hash_shape`, `_unique` | 64 hex characters, unique                    | Only hashes, never tokens.                |
| `password_resets_expiry`                      | Expires after creation, at most 1 hour later | No month-long links from any writer.      |
| `password_resets_used_in_time`                | Used only before expiry                      | No late use slipping in.                  |
| `candidates_password_hash_shape`              | bcrypt only                                  | A reset can never store a plain password. |

**Transaction boundary:** using the link, changing the password and cancelling other links commit together.

``` code
CREATE TABLE candidates (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         VARCHAR(254) NOT NULL CONSTRAINT candidates_email_lower CHECK (email = lower(email)),
    full_name     VARCHAR(100) NOT NULL,
    password_hash VARCHAR(100) NOT NULL CONSTRAINT candidates_password_hash_shape
                  CHECK (password_hash ~ '^\{bcrypt\}\$2[aby]\$(1[0-9]|2[0-9]|3[01])\$[./A-Za-z0-9]{53}$'),
    status        VARCHAR(10)  NOT NULL DEFAULT 'ACTIVE' CONSTRAINT candidates_status_known CHECK (status IN ('ACTIVE', 'SUSPENDED')),
    CONSTRAINT candidates_email_unique UNIQUE (email)
);

-- Only a SHA-256 of each token is kept: a copy of this table cannot be used to reset anyone's password.
-- (A fast hash is right here, unlike for passwords: the token is 256 random bits, not something a person chose.)
CREATE TABLE password_resets (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    candidate_id BIGINT      NOT NULL CONSTRAINT password_resets_candidate_fk REFERENCES candidates (id) ON DELETE CASCADE,
    token_hash   CHAR(64)    NOT NULL CONSTRAINT password_resets_token_hash_unique UNIQUE
                             CONSTRAINT password_resets_token_hash_shape CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    created_at   TIMESTAMPTZ NOT NULL,
    expires_at   TIMESTAMPTZ NOT NULL,
    used_at      TIMESTAMPTZ,
    CONSTRAINT password_resets_expiry CHECK (expires_at > created_at AND expires_at <= created_at + interval '1 hour'),
    CONSTRAINT password_resets_used_in_time CHECK (used_at IS NULL OR (used_at >= created_at AND used_at < expires_at))
);
CREATE INDEX password_resets_candidate ON password_resets (candidate_id);

-- Simulated email: a row is written here; nothing is sent.
CREATE TABLE outbox_emails (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    to_email   VARCHAR(254) NOT NULL,
    subject    VARCHAR(200) NOT NULL,
    body       TEXT         NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL
);
```

# 3 · Go deeper: Production

Email is not instant  
30 minutes is a demo rule; measure how long your email provider takes before you shorten it.

Referrer leaks  
The reset page should send no `Referer` with the token (a `Referrer-Policy: no-referrer` header) and load no third-party scripts.

Old rows  
Delete used and expired rows on a schedule; they are useless and still personal data.

Abuse  
The per-account limit protects one inbox; limits per IP address and a CAPTCHA protect the service from mass requests.

# 3 · Go deeper: Interview

## Interview takeaways

What makes a reset token safe?

Enough randomness (128+ bits from a secure generator), a short expiry, single use, and storing only its hash.

Why store a hash of the token?

A copy of the table, from a backup or a leak, then opens nothing; the email holds the only usable copy.

How do you avoid account enumeration in a reset form?

Give the same reply, status and roughly the same timing for every email; send the email only if the account exists.

How do you make a token single-use under concurrency?

Check and mark it in one conditional statement: UPDATE … WHERE unused AND unexpired RETURNING; only one request can get a row back.

What should happen after a reset?

Cancel other reset links, notify the owner, and end other sessions or tokens.

## Self-check rubric

| Area        | Meets the bar                         | Above the bar                                          |
|-------------|---------------------------------------|--------------------------------------------------------|
| Correctness | All 17 tests pass.                    | You ran the flawed version and explained each failure. |
| Tokens      | Random, hashed, expiring, single-use. | Why a fast hash is fine here.                          |
| Privacy     | One reply for every email.            | The timing that still differs.                         |
| Concurrency | One conditional UPDATE.               | Why check-then-update races.                           |

# 3 · Go deeper: Review

## The pull request

A teammate makes resets "friendlier": tell people when they mistype their email, keep the link working "in case the first attempt fails", and drop the open-link count "to simplify". Read the file and list every problem before opening the findings.

#### `review/PasswordResets.java`

``` code
package com.hireloop.resets;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.HexFormat;
import java.util.Locale;
import java.util.Optional;

@Service
class PasswordResets {

    /** Demo rule: at most 3 links waiting at once per account, so the form cannot flood someone's inbox. */
    static final int MAX_OPEN_LINKS = 3;

    private static final SecureRandom RANDOM = new SecureRandom();

    private final JdbcClient jdbc;
    private final PasswordEncoder passwords;
    private final Clock clock;
    private final String link;
    private final Duration validFor;

    PasswordResets(JdbcClient jdbc, PasswordEncoder passwords, Clock clock,
                   @Value("${hireloop.reset-link}") String link, @Value("${hireloop.reset-valid-minutes}") long minutes) {
        this.jdbc = jdbc;
        this.passwords = passwords;
        this.clock = clock;
        this.link = link;
        this.validFor = Duration.ofMinutes(minutes);
    }

    /**
     * Sends a link if, and only if, an active account has this email. The caller never learns which: the controller
     * gives one reply for every case.
     */
    @Transactional
    void request(String typedEmail) {
        String email = typedEmail.strip().toLowerCase(Locale.ROOT);
        Instant now = clock.instant();
        Optional<Long> candidate = jdbc.sql("SELECT id FROM candidates WHERE email = ? AND status = 'ACTIVE' FOR UPDATE").param(email).query(Long.class).optional();
        if (candidate.isEmpty()) {
            // Friendlier: tell people when they mistyped their email.
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No account with this email");
        }
        byte[] secret = new byte[32];   // 256 random bits: guessing one is hopeless
        RANDOM.nextBytes(secret);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(secret);
        jdbc.sql("INSERT INTO password_resets (candidate_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)")
                .params(candidate.get(), sha256(token), utc(now), utc(now.plus(validFor))).update();
        jdbc.sql("INSERT INTO outbox_emails (to_email, subject, body, created_at) VALUES (?, ?, ?, ?)")
                .params(email, "Reset your Hireloop password",
                        "Someone asked to reset the password for this account. If it was you, open this link within "
                                + validFor.toMinutes() + " minutes:\n" + link + token + "\nIf it was not you, ignore this email.", utc(now)).update();
    }

    /**
     * Uses the link: one UPDATE both checks it (unused, not expired) and marks it used, so two requests with the same
     * link cannot both pass. Then the password changes and every other open link for the account stops working.
     */
    @Transactional
    void complete(String token, String newPassword) {
        Instant now = clock.instant();
        // Keep the link valid until it expires, in case the first attempt fails on the user's side.
        Long candidate = token.matches("[A-Za-z0-9_-]{43}") ? jdbc.sql("SELECT candidate_id FROM password_resets WHERE token_hash = ? AND expires_at > ?")
                .params(sha256(token), utc(now)).query(Long.class).optional().orElse(null) : null;
        if (candidate == null) {
            // One message for unknown, used and expired links: none of them says anything about the account.
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "This link is invalid or has expired; ask for a new one");
        }
        jdbc.sql("UPDATE candidates SET password_hash = ? WHERE id = ?").params(passwords.encode(newPassword), candidate).update();
    }

    static String sha256(String token) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.US_ASCII)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static OffsetDateTime utc(Instant instant) {
        return instant.atOffset(ZoneOffset.UTC);
    }
}
```

## Findings

1"No account with this email"

A friendly 404 for unknown emails turns the form into a list checker for attackers.

**Test evidence:** `anUnknownEmailGetsTheSameReplyAndNoEmail`, `theOldFormToldAttackersWhichEmailsHaveAccounts` and `aSuspendedAccountIs403AndGetsNoLink` fail.

2The link is never marked used

"In case the first attempt fails" means anyone with the email can reset again for the next 30 minutes, and ten parallel uses all succeed.

**Test evidence:** `aNewLinkWorksOnceAndOnlyFor30Minutes` and `oneLinkUsedTwiceAtTheSameMomentWorksOnce` fail.

3Other open links stay valid

An older email in a stolen inbox still resets the password after the owner has reset it.

**Test evidence:** `aNewPasswordCancelsEveryOtherOpenLink` fails.

4No limit on links

Removing the open-link check lets anyone flood a person's inbox with resets.

**Test evidence:** `floodingTheFormSendsAtMostThreeLinks` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class              | Fixed version | Flawed version |
|-------------------------|---------------|----------------|
| `ResetDatabaseTest`     | 2 / 2         | 2 / 2          |
| `ResetContractTest`     | 4 / 4         | 3 / 4          |
| `ResetSecurityTest`     | 7 / 7         | 3 / 7          |
| `ReusableTokenTrapTest` | 4 / 4         | 2 / 4          |

Every change looks like kindness to users; each one is kindness to attackers too.
