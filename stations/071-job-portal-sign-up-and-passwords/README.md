# Station 071 · Job portal sign-up and passwords

Working Systems · 0–2 years · Core · Recruitment · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · Spring Security 7 SecurityFilterChain · BCrypt via DelegatingPasswordEncoder · CORS · JdbcClient · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Candidates and their passwords are demo data, not Hireloop's. No email is sent and no real account exists.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 14 tests.

# 1 · Understand

## The problem in real life

1.  **The leak**

    A copy of Hireloop's candidate table got out. Passwords were stored as MD5 hashes.

2.  **Cracked in a coffee break**

    MD5 is fast. An attacker hashes a list of common passwords and compares: every match is an account. Two people with the same password even had the same hash. 80,000 accounts were exposed.

3.  **The fix**

    Store bcrypt hashes: salted, and slow on purpose. Old MD5 hashes are replaced with bcrypt the next time each candidate signs in.

Assume the password table will leak one day. Store it so the leak is useless.

## What are we building?

`POST /candidates/signup` creates an account with a bcrypt-hashed password; `GET /candidates/me` returns the signed-in candidate's own profile.

## An everyday analogy

A bank does not keep your PIN on a card in the drawer. It keeps something that can check a PIN but cannot give it back, and makes each check take time, so trying a million PINs is hopeless.

## How it works in 4 steps

1.  **Sign-up**: check the email and a long-enough password, lower-case the email.
2.  **Hash** the password with bcrypt: a new salt each time, a deliberate cost.
3.  **Store** only the hash; the database refuses anything that is not one.
4.  **Sign-in**: Spring Security hashes what was sent the same way and compares; an old MD5 hash is replaced with bcrypt on success.

Check yourself: two candidates choose the same password. Do their stored hashes match?

With the old MD5: yes, so one cracked password exposes both. With bcrypt: no, each hash has its own salt. The trap test shows the first; the stored hashes in the captures show the second.

## What this station is not

- **No password reset.** That is station 072.
- **No tokens or sessions.** Credentials come with each request; tokens are station 073.
- **No email verification.** A real sign-up would confirm the email address.

## Key terms

| Term             | Simple meaning                                                               | Everyday example                                         | In this project           |
|------------------|------------------------------------------------------------------------------|----------------------------------------------------------|---------------------------|
| **Hash**         | A one-way fingerprint of a password: easy to compute, impossible to reverse. | A fingerprint identifies a person but is not the person. | `password_hash`           |
| **Fast hash**    | MD5 or SHA-256: billions of guesses per second on a graphics card.           | A lock that can be tried a billion times a second.       | the old MD5 hashes        |
| **Salt**         | Random text mixed in, so the same password gives a different hash each time. | Two people with the same PIN, but different locks.       | inside every bcrypt hash  |
| **Work factor**  | How slow the hash is on purpose; raised as computers get faster.             | A lock that takes a second to try, every time.           | bcrypt cost 10            |
| **Filter chain** | The checks every request passes before a controller sees it.                 | Security at a building's entrance.                       | `SecurityFilterChain`     |
| **CORS**         | Which other websites a browser lets call this API.                           | A guest list at the door, for browsers.                  | `corsConfigurationSource` |

# 2 · Build: Spec

## Business problem

**Hireloop** (a fictional job portal) stored passwords with MD5. A leak exposed 80,000 accounts.

## Acceptance criteria

Demo data: two accounts imported from the old system, still with MD5 hashes.

1.  **Given** a valid sign-up, **then** `201`, a bcrypt hash stored, and no password or hash in any response.
2.  **Given** the same email in other capitals, **then** `409`.
3.  **Given** a password under 12 characters, over 64, or over 72 bytes, **then** `400`.
4.  **Given** no credentials, a wrong password or an unknown email, **then** the same `401`.
5.  **Given** a legacy account's correct password, **then** `200`, and its hash is now bcrypt.
6.  **Given** a browser on another website, **then** the CORS preflight is refused (`403`).

## Requirements

- New passwords are hashed with bcrypt (cost 10); old MD5 hashes are only ever verified, then replaced.
- The database refuses plain text, bare digests and weak bcrypt costs.
- Responses never say whether an email has an account.
- Only Hireloop's web app may call the API from a browser.

## Learning objectives

- Configure a `SecurityFilterChain` for a stateless API.
- Hash with bcrypt through a `PasswordEncoder`, and migrate old hashes.
- Explain why CSRF does not apply here and what CORS does.
- Back the rules with database constraints.

# 2 · Build: API contract

## Endpoints

| Method | Path                 | Purpose                                                                              |
|--------|----------------------|--------------------------------------------------------------------------------------|
| `POST` | `/candidates/signup` | `{email, fullName, password}`; open to everyone; `201` with `{id, email, fullName}`. |
| `GET`  | `/candidates/me`     | The signed-in candidate (HTTP Basic: email and password).                            |

## Status codes

| Status    | When                                                                                     |
|-----------|------------------------------------------------------------------------------------------|
| 200 / 201 | Profile / account created                                                                |
| 400       | Not an email; password under 12 or over 64 characters, or over 72 bytes; a field missing |
| 401       | No credentials, or credentials that do not match an account (one answer for both)        |
| 403       | A browser preflight from a website other than Hireloop's                                 |
| 409       | An account with that email exists                                                        |

## Captured examples

Captured with curl from the running app on 19 Oct 2026. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: sign-up

**Why:** the email is lower-cased; nothing about the password comes back.

Request

``` code
POST /candidates/signup HTTP/1.1
Content-Type: application/json

{
  "email": "Nisha@Example.com",
  "fullName": "Nisha Rao",
  "password": "correct-horse-battery"
}
```

Response

``` code
HTTP/1.1 201 
Location: /candidates/me
Content-Type: application/json

{
  "id": 3,
  "email": "nisha@example.com",
  "fullName": "Nisha Rao"
}
```

### Case 2: the profile, signed in

**Why:** "me" comes from the credentials.

Request

``` code
GET /candidates/me HTTP/1.1
Authorization: Basic bmlzaGFAZXhhbXBsZS5jb206Y29ycmVjdC1ob3JzZS1iYXR0ZXJ5
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 59

{
  "id": 3,
  "email": "nisha@example.com",
  "fullName": "Nisha Rao"
}
```

### Case 3: a wrong password

**Why:** `401`.

Request

``` code
GET /candidates/me HTTP/1.1
Authorization: Basic bmlzaGFAZXhhbXBsZS5jb206d3JvbmctcGFzc3dvcmQtaGVyZQ==
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="hireloop"
Content-Type: application/problem+json
Content-Length: 113

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid email and password.",
  "instance": "/candidates/me"
}
```

### Case 4: an email with no account

**Why:** exactly the same `401` as case 3.

Request

``` code
GET /candidates/me HTTP/1.1
Authorization: Basic bm9ib2R5QGV4YW1wbGUuY29tOndyb25nLXBhc3N3b3JkLWhlcmU=
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="hireloop"
Content-Type: application/problem+json
Content-Length: 113

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid email and password.",
  "instance": "/candidates/me"
}
```

### Case 5: the same email again

**Why:** `409`, pointing to sign-in or reset.

Request

``` code
POST /candidates/signup HTTP/1.1
Content-Type: application/json

{
  "email": "nisha@example.com",
  "fullName": "Someone Else",
  "password": "another-long-password"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "An account with this email exists; sign in or reset the password",
  "instance": "/candidates/signup",
  "status": 409,
  "title": "Conflict"
}
```

### Case 6: an imported account signs in

**Why:** its MD5 hash checks out once, and is replaced (below).

Request

``` code
GET /candidates/me HTTP/1.1
Authorization: Basic cHJpeWFAZXhhbXBsZS5jb206c3VtbWVyMjAyNCE=
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

### Case 7: a preflight from another website

**Why:** CORS refuses it.

Request

``` code
OPTIONS /candidates/signup HTTP/1.1
Origin: https://evil.example
Access-Control-Request-Method: POST
```

Response

``` code
HTTP/1.1 403

Invalid CORS request
```

## The stored hashes, before and after

From `psql` in `docs/capture.sh`: before the requests (`hashes-before.txt`) and after (`hashes-after.txt`).

``` code
       email       |             password_hash             
-------------------+---------------------------------------
 priya@example.com | {MD5}3fb39f7f2966115ff647c5781c8b4ce1
 arjun@example.com | {MD5}694e990c6df30c3dad9f3529e279083e
(2 rows)
```

``` code
       email       |                            password_hash                             
-------------------+----------------------------------------------------------------------
 priya@example.com | {bcrypt}$2a$10$stt9V9IpRerIGx37O9HSEuD6As73z84Zw2MiE0W9MLNnWmQMoh90C
 arjun@example.com | {MD5}694e990c6df30c3dad9f3529e279083e
 nisha@example.com | {bcrypt}$2a$10$UP48bv73MW0qLn8cUO8/pOJCoaQkmAI9x4pmyFFq96WEfobE60lHO
(3 rows)
```

Priya's MD5 hash became bcrypt at her sign-in (case 6); Arjun has not signed in, so his is still MD5. Nisha's hash shows the parts of bcrypt: `$2a$` the version, `10` the cost, then 22 characters of salt and the hash.

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                          | What happens                                  | Proved by                                     |
|-------------------------------------------------------------------------------|-----------------------------------------------|-----------------------------------------------|
| Sign up, then read the profile                                                | `201`, then own profile                       | `signUpThenReadOwnProfile`                    |
| What is stored                                                                | A bcrypt hash, never the password             | `theStoredHashIsBcryptNeverThePassword`       |
| The same email, other capitals                                                | `409`                                         | `aDuplicateEmailIs409AnyCase`                 |
| Too short, too long, too many bytes, missing fields                           | `400`                                         | `badSignupsAre400`                            |
| Unknown email against wrong password                                          | Identical `401`s                              | `anUnknownEmailAndAWrongPasswordLookTheSame`  |
| Another candidate's profile                                                   | Not reachable: "me" is the signed-in identity | `oneCandidateOnlyEverSeesTheirOwnProfile`     |
| A browser on another site                                                     | Preflight refused                             | `theApiIsReachableOnlyFromHireloopsOwnWebApp` |
| SQL-looking input, control characters                                         | `400` or `401`, never run                     | `oddInputIsRejectedNotExecuted`               |
| Plain text, bare digest, {noop}, weak cost, upper-case email written directly | Refused by named constraints                  | `namedConstraintsHoldWithoutJava`             |

## The trap

Plausible but wrong

Fast hashes like MD5 or SHA-256 without a work factor.

- **Cracked from a list.** The test takes Priya's leaked MD5 hash and hashes 25 common passwords: one of them matches. Real attackers use lists of millions, and a fast hash lets them try all of them per account in moments.
- **The same leak with bcrypt.** The bcrypt hash of the same password contains no MD5 to compare; every guess costs the full, deliberate work of bcrypt, with that hash's own salt.
- **Old accounts move over by themselves.** The imported MD5 hash is checked once at sign-in; Spring then calls `updatePassword` and the row holds bcrypt.

While building, each fix was undone once: no MD5 verifier turned 2 tests red (sign-in on a legacy row failed with an error instead of a `401`, so even "unknown and wrong look the same" broke); no upgrade service 1; no byte check 1; no lower-casing of emails 2; no hash-shape CHECK 1; the CORS bean under another name 1.

``` code
package com.hireloop.candidates;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old system hashed passwords with a single MD5 pass. This shows why that is broken, and that
 * bcrypt fixes it: a leak of MD5 hashes is cracked instantly from a tiny list; bcrypt's hashes are not.
 */
class FastHashTrapTest extends ApiTest {

    @Autowired
    PasswordEncoder passwords;

    /** The 25 passwords an attacker tries first; the real breach lists run to millions, and MD5 clears them in seconds. */
    static final List<String> COMMON = List.of("123456", "password", "123456789", "12345678", "qwerty", "abc123", "football",
            "monkey", "letmein", "111111", "iloveyou", "admin", "welcome", "summer2024!", "login", "princess", "solo",
            "passw0rd", "starwars", "dragon", "master", "hello", "freedom", "whatever", "trustno1");

    private static String md5(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("MD5").digest(text.getBytes()));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    @Test
    void anMd5LeakIsCrackedFromACommonPasswordList() {
        String leaked = md5("summer2024!");   // Priya's password, as the old table stored it
        String cracked = COMMON.stream().filter(guess -> md5(guess).equals(leaked)).findFirst().orElseThrow();
        assertThat(cracked).isEqualTo("summer2024!");   // one pass of MD5 per guess: the whole list in well under a millisecond
    }

    @Test
    void theSameLeakOfBcryptHashesRevealsNothing() {
        String stored = passwords.encode("summer2024!");   // what the new system stores
        assertThat(stored).startsWith("{bcrypt}$2");
        assertThat(COMMON.stream().anyMatch(guess -> stored.contains(md5(guess)))).isFalse();   // the MD5 is nowhere in the bcrypt hash
        assertThat(passwords.matches("summer2024!", stored)).isTrue();   // only the real password verifies, and each check is deliberately slow
    }

    @Test
    void aLegacyMd5AccountIsUpgradedToBcryptOnFirstSignIn() throws Exception {
        assertThat(hashOf("priya@example.com")).startsWith("{MD5}");
        me("priya@example.com", "summer2024!").andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.status().isOk());
        assertThat(hashOf("priya@example.com")).startsWith("{bcrypt}$2");   // re-hashed the moment the right password was seen
        me("priya@example.com", "summer2024!").andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.status().isOk());   // still works after the upgrade
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

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Sign up, sign in, and look at what was stored:

``` code
curl -X POST http://localhost:8080/candidates/signup -H 'Content-Type: application/json' \
  -d '{"email": "you@example.com", "fullName": "You", "password": "a-long-passphrase"}'
curl -u 'you@example.com:a-long-passphrase' http://localhost:8080/candidates/me
docker compose exec postgres psql -U hireloop -d hireloop -c "SELECT email, password_hash FROM candidates"
```

Sign up twice with the same password under two emails: the two hashes differ.

## Troubleshooting

| You see                                             | Cause                                                          | Fix                                                                   |
|-----------------------------------------------------|----------------------------------------------------------------|-----------------------------------------------------------------------|
| Every origin passes CORS                            | The `CorsConfigurationSource` bean has another name.           | Name it `corsConfigurationSource`. Found while building this station. |
| `There is no PasswordEncoder mapped for the id "…"` | A stored hash with a prefix the encoder does not know.         | Add a verifier for it, or reset those accounts.                       |
| `password cannot be more than 72 bytes`             | bcrypt's input limit, enforced by Spring Security.             | Check the byte length first and answer `400`, as the controller does. |
| `candidates_password_hash_shape` violated           | Something tried to store a password that is not a bcrypt hash. | Always store `passwordEncoder.encode(…)`.                             |

## Project layout

``` tree
stations/071-job-portal-sign-up-and-passwords/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/hireloop/candidates/
│   ├── SecurityConfig.java   ├── CandidateAccounts.java   ├── CandidateController.java
│   ├── ProblemResponses.java   └── CandidatesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__candidates.sql, V2__legacy_candidates.sql
├── src/test/java/com/hireloop/candidates/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/hireloop/candidates/SecurityConfig.java`

Does  
The filter chain, CORS and the password encoder.

Why  
Sign-up open, all else authenticated; stateless Basic; bcrypt for new hashes, MD5 only to verify old ones.

Without it  
Every endpoint open, or plain-text and MD5 hashes accepted forever.

- CSRF is off because nothing here uses cookies or sessions: a browser never attaches these credentials on its own. With cookie sessions, CSRF protection must stay on.
- The CORS bean must be called `corsConfigurationSource`; under another name it is ignored. Found while building this station.
- Spring's default encoder list also accepts `{noop}` (plain text); this list holds only bcrypt and MD5.

#### `src/main/java/com/hireloop/candidates/CandidateAccounts.java`

Does  
Finds a candidate by email for Spring Security, and stores re-hashed passwords.

Why  
As a `UserDetailsPasswordService`, Spring hands it the new bcrypt hash after an old hash checks out.

Without it  
Legacy MD5 hashes staying in the table for years.

#### `src/main/java/com/hireloop/candidates/CandidateController.java`

Does  
Sign-up and "me".

Why  
Lower-cased emails, a 72-byte check for bcrypt, the hash made by the encoder; "me" from the verified identity.

Without it  
Duplicate accounts by capital letters, or a profile chosen by an id in the URL.

#### `src/main/java/com/hireloop/candidates/ProblemResponses.java`

401 and 403 in the same problem JSON as every other error.

#### `src/main/resources/db/migration/V1__candidates.sql`

Does  
The table, with a CHECK on the hash's shape.

Why  
Plain text, bare digests, `{noop}` and cheap bcrypt costs are refused for every writer.

Without it  
A script or a hurried fix storing passwords in the clear.

#### `src/main/resources/db/migration/V2__legacy_candidates.sql`

Two accounts imported with the old MD5 hashes.

#### `src/main/resources/application.yaml`

The one allowed browser origin.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/hireloop/candidates/CandidatesApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                  | Result |
|---------------|-------------------------------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `CandidateContractTest` (4) | pass   |
| Every station | Reproduce the failure before the fix                              | `FastHashTrapTest` (3)      | pass   |
| Database      | Rollback and constraint tests against a real database             | `CandidateDatabaseTest` (2) | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `CandidateSecurityTest` (5) | pass   |

"Not found" here is the unknown email, answered like a wrong password on purpose. "Another user's data": there is no endpoint that takes an id, so the test shows one candidate's credentials can only ever reach their own profile.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.hireloop.candidates.FastHashTrapTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.hireloop.candidates.CandidateDatabaseTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.hireloop.candidates.CandidateSecurityTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.hireloop.candidates.CandidateContractTest
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/hireloop/candidates/FastHashTrapTest.java`

Written first: an MD5 leak cracked from a short list, the same with bcrypt, and the upgrade at sign-in.

#### `src/test/java/com/hireloop/candidates/CandidateSecurityTest.java`

401s that look alike, own profile only, CORS, odd input.

#### `src/test/java/com/hireloop/candidates/CandidateDatabaseTest.java`

The hash-shape CHECK and the email rules with plain SQL, and a rolled-back insert.

#### `src/test/java/com/hireloop/candidates/CandidateContractTest.java`

Sign-up and profile through HTTP.

#### `src/test/java/com/hireloop/candidates/ApiTest.java`

Shared setup: the legacy accounts restored after each test.

#### `src/test/java/com/hireloop/candidates/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/hireloop/candidates/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ChangePasswordChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 14 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 18 tests pass (14 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Change the password

Add `PUT /candidates/me/password` `{currentPassword, newPassword}`: `204`; the current password must be right (`422`), the new one follows the sign-up rules (`400`).

**Done when:** both tests in `ChangePasswordChallengeTest` pass.

Hints

- Check the current password with `passwordEncoder.matches` against the stored hash.
- Store `passwordEncoder.encode(newPassword)`, never the text.

#### `challenge/ChangePasswordChallengeTest.java`

``` code
package com.hireloop.candidates;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: PUT /candidates/me/password {currentPassword, newPassword} changes the signed-in candidate's password:
 * 204. The current password must be given again (422 if wrong), and the new one follows the sign-up rules (400).
 */
class ChangePasswordChallengeTest extends ApiTest {

    private org.springframework.test.web.servlet.ResultActions change(String signedInWith, String current, String next) throws Exception {
        return mvc.perform(put("/candidates/me/password").with(httpBasic("arjun@example.com", signedInWith)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"currentPassword\":\"%s\",\"newPassword\":\"%s\"}".formatted(current, next)));
    }

    @Test
    void theOldPasswordStopsWorking() throws Exception {
        change("Hireloop@123", "Hireloop@123", "a-much-longer-passphrase").andExpect(status().isNoContent());
        me("arjun@example.com", "Hireloop@123").andExpect(status().isUnauthorized());
        me("arjun@example.com", "a-much-longer-passphrase").andExpect(status().isOk());
    }

    @Test
    void theCurrentPasswordIsCheckedAndTheNewOneFollowsTheRules() throws Exception {
        change("Hireloop@123", "not-my-password", "a-much-longer-passphrase").andExpect(status().isUnprocessableContent());
        change("Hireloop@123", "Hireloop@123", "short").andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Lock after five wrong passwords

After 5 wrong passwords in a row, lock the account for 15 minutes; the right password then gets the same `401`. A good sign-in resets the count.

**Done when:** both tests in `LockoutChallengeTest` pass.

Hints

- Spring Security publishes `AuthenticationFailureBadCredentialsEvent` and `AuthenticationSuccessEvent`; listen with `@EventListener`.
- Two columns in a new migration: a counter and `locked_until`.
- Return `accountLocked(true)` from `loadUserByUsername` while locked.

#### `challenge/LockoutChallengeTest.java`

``` code
package com.hireloop.candidates;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: after 5 wrong passwords in a row an account is locked for 15 minutes: even the right password gets
 * the same 401 as before, so the lock reveals nothing. A successful sign-in resets the count.
 */
class LockoutChallengeTest extends ApiTest {

    @Test
    void fiveWrongPasswordsLockTheAccount() throws Exception {
        for (int i = 0; i < 5; i++) {
            me("arjun@example.com", "guess-number-" + i).andExpect(status().isUnauthorized());
        }
        me("arjun@example.com", "Hireloop@123").andExpect(status().isUnauthorized());
        assertThat(jdbc.sql("SELECT locked_until > now() FROM candidates WHERE email = 'arjun@example.com'").query(Boolean.class).single()).isTrue();
    }

    @Test
    void aSuccessfulSignInResetsTheCount() throws Exception {
        for (int i = 0; i < 4; i++) {
            me("priya@example.com", "guess-number-" + i).andExpect(status().isUnauthorized());
        }
        me("priya@example.com", "summer2024!").andExpect(status().isOk());
        for (int i = 0; i < 4; i++) {
            me("priya@example.com", "guess-again-" + i).andExpect(status().isUnauthorized());
        }
        me("priya@example.com", "summer2024!").andExpect(status().isOk());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Refusing passwords that have already leaked

Long passwords can still be leaked ones. Design a check against a breached-password list at sign-up without sending the password anywhere: hash it, send only the first five characters of the hash to a range API, and compare the returned suffixes locally (k-anonymity). Where does the check run, what happens if the service is down, and when would you move from bcrypt to argon2?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: crack an MD5 leak from a list.
2.  Pick bcrypt behind `DelegatingPasswordEncoder`, with MD5 only to verify old hashes.
3.  Let Spring upgrade old hashes at sign-in through `UserDetailsPasswordService`.
4.  Configure the filter chain, CORS, and the database CHECK on hash shapes.

## Design alternatives and trade-offs

| Approach                                                 | What it costs                                                                      | Verdict                   |
|----------------------------------------------------------|------------------------------------------------------------------------------------|---------------------------|
| bcrypt via DelegatingPasswordEncoder, upgrade at sign-in | A slow hash per sign-in (by design).                                               | Chosen                    |
| MD5 or SHA-256, salted or not                            | Billions of guesses per second.                                                    | The trap                  |
| argon2id                                                 | Memory-hard, the current first choice in OWASP guidance; needs Bouncy Castle here. | Better, more setup        |
| Re-hash every MD5 hash at once: bcrypt(md5)              | No waiting for sign-ins; a nested scheme forever.                                  | Valid for a fast cut-over |
| Force a reset for every legacy account                   | Clean; annoys every user.                                                          | After a known breach      |

## Database design

| Object                                              | What                                                         | Why                                                      |
|-----------------------------------------------------|--------------------------------------------------------------|----------------------------------------------------------|
| `candidates_password_hash_shape`                    | CHECK: bcrypt with cost 10–31, or a tagged legacy MD5 digest | No plain text, bare digests or `{noop}` from any writer. |
| `candidates_email_lower`, `candidates_email_unique` | CHECK and UNIQUE                                             | One account per email, whatever the capitals.            |

``` code
CREATE TABLE candidates (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         VARCHAR(254) NOT NULL CONSTRAINT candidates_email_lower CHECK (email = lower(email)),
    full_name     VARCHAR(100) NOT NULL,
    -- Only a bcrypt hash (cost 10 or more), or a legacy {MD5} hash from the old system that is replaced at the next sign-in.
    -- Plain text and bare digests are refused, whoever writes the row.
    password_hash VARCHAR(100) NOT NULL CONSTRAINT candidates_password_hash_shape
                  CHECK (password_hash ~ '^\{bcrypt\}\$2[aby]\$(1[0-9]|2[0-9]|3[01])\$[./A-Za-z0-9]{53}$' OR password_hash ~ '^\{MD5\}[0-9a-f]{32}$'),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT candidates_email_unique UNIQUE (email)
);
```

# 3 · Go deeper: Production

After a breach  
Hashing better does not undo a leak that happened. Tell users, force resets for leaked accounts, and watch for credential stuffing.

Cost of bcrypt  
Each sign-in costs real CPU. Rate-limit sign-in attempts, and measure the cost on production hardware before raising it.

Basic over HTTPS only  
HTTP Basic sends the password with every request: only ever over TLS. Station 073 replaces it with tokens.

Logs  
Never log request bodies of sign-up or password endpoints.

# 3 · Go deeper: Interview

## Interview takeaways

Why not store passwords with SHA-256?

It is designed to be fast; an attacker with the hashes can try billions of guesses per second. Password hashes must be salted and deliberately slow: bcrypt, scrypt, argon2.

What is a salt for?

It makes each hash unique, so equal passwords do not share hashes and precomputed tables are useless.

How do you migrate old hashes?

Keep a verifier for the old format, and re-hash with the new algorithm when the user next signs in; Spring's DelegatingPasswordEncoder and UserDetailsPasswordService do exactly this.

Does this API need CSRF protection?

Not while credentials come only in the Authorization header: browsers never add it on their own. With cookie sessions, yes.

What does CORS protect?

It tells browsers which other websites may read responses from this API; it does not stop curl or servers, so it is not authentication.

## Self-check rubric

| Area            | Meets the bar                              | Above the bar                                          |
|-----------------|--------------------------------------------|--------------------------------------------------------|
| Correctness     | All 14 tests pass.                         | You ran the flawed version and explained each failure. |
| Hashing         | bcrypt with a salt and a cost.             | Migrating old hashes at sign-in.                       |
| Spring Security | A filter chain with open and closed paths. | Why CSRF is off here and when it must be on.           |
| Privacy         | No account enumeration at sign-in.         | Also at sign-up (station 072).                         |

# 3 · Go deeper: Review

## The pull request

A teammate speeds up sign-in: "SHA-256 is modern and much faster than bcrypt". They also relax the password minimum to six characters, keep emails exactly as typed, and open CORS to "\*" for preview builds. Read the two files and list every problem before opening the findings.

#### `review/SecurityConfig.java`

``` code
package com.hireloop.candidates;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;

@Configuration
class SecurityConfig {

    /** The chain every request passes: sign-up is open, everything else needs a valid email and password. */
    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.POST, "/candidates/signup").permitAll()
                        .anyRequest().authenticated())
                .httpBasic(basic -> basic.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .cors(cors -> {})
                // No cookies and no sessions: a browser never sends these credentials by itself, so there is nothing for CSRF to forge.
                .csrf(csrf -> csrf.disable());
        return http.build();
    }

    /**
     * Browsers may call this API only from Hireloop's own web app. The bean must be named corsConfigurationSource:
     * that is the name http.cors() looks up. Under another name it is silently ignored and every origin gets through.
     */
    @Bean
    CorsConfigurationSource corsConfigurationSource(@Value("${hireloop.allowed-origin}") String origin) {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(List.of("*"));   // so the preview builds on random hosts can call us too
        config.setAllowedMethods(List.of("GET", "POST"));
        config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }

    /** SHA-256 is a modern, secure hash, and much faster than bcrypt: sign-in stays snappy under load. */
    @Bean
    PasswordEncoder passwordEncoder() {
        return new PasswordEncoder() {
            @Override
            public String encode(CharSequence raw) {
                try {
                    return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw.toString().getBytes(StandardCharsets.UTF_8)));
                } catch (Exception e) {
                    throw new IllegalStateException(e);
                }
            }

            @Override
            public boolean matches(CharSequence raw, String encoded) {
                return encode(raw).equals(encoded);
            }
        };
    }
}
```

#### `review/CandidateController.java`

``` code
package com.hireloop.candidates;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.net.URI;
import java.nio.charset.StandardCharsets;

@RestController
class CandidateController {

    /** Six characters is what most sites ask for; longer minimums annoy candidates. */
    record Signup(@NotNull @Email @Size(max = 254) String email, @NotBlank @Size(max = 100) String fullName,
                  @NotNull @Size(min = 6, max = 64) String password) {
    }

    record Candidate(long id, String email, String fullName) {
    }

    private final JdbcClient jdbc;
    private final PasswordEncoder passwords;

    CandidateController(JdbcClient jdbc, PasswordEncoder passwords) {
        this.jdbc = jdbc;
        this.passwords = passwords;
    }

    @PostMapping("/candidates/signup")
    ResponseEntity<Candidate> signup(@Valid @RequestBody Signup body) {
        if (body.password().getBytes(StandardCharsets.UTF_8).length > 72) {
            // bcrypt only reads the first 72 bytes; Spring Security refuses longer input rather than ignore the rest.
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "The password is longer than 72 bytes");
        }
        String email = body.email().strip();   // keep the email exactly as the candidate typed it
        try {
            long id = jdbc.sql("INSERT INTO candidates (email, full_name, password_hash) VALUES (?, ?, ?) RETURNING id")
                    .params(email, body.fullName().strip(), passwords.encode(body.password())).query(Long.class).single();
            return ResponseEntity.created(URI.create("/candidates/me")).body(new Candidate(id, email, body.fullName().strip()));
        } catch (DuplicateKeyException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "An account with this email exists; sign in or reset the password");
        }
    }

    /** "Me" is whoever signed in: there is no id to change in the URL. */
    @GetMapping("/candidates/me")
    Candidate me(Authentication auth) {
        return jdbc.sql("SELECT id, email, full_name FROM candidates WHERE email = ?").param(auth.getName()).query(Candidate.class).single();
    }
}
```

## Findings

1SHA-256 instead of bcrypt

"Modern and fast" is exactly the problem: one fast, unsalted hash per password. The database's hash-shape CHECK refuses it, so every sign-up becomes a 500; without the CHECK the weak hashes would have been stored quietly.

**Test evidence:** `signUpThenReadOwnProfile`, `theStoredHashIsBcryptNeverThePassword`, `oneCandidateOnlyEverSeesTheirOwnProfile` (its sign-ups fail) and `theSameLeakOfBcryptHashesRevealsNothing` fail.

2No verifier for the imported MD5 hashes

Replacing the encoder drops the MD5 verifier: the legacy accounts can never sign in or be upgraded.

**Test evidence:** `aLegacyMd5AccountIsUpgradedToBcryptOnFirstSignIn` fails.

3Six-character passwords

Short passwords are the first a list tries.

**Test evidence:** `badSignupsAre400` fails.

4Emails kept as typed

`Sam@` and `sam@` become two accounts, and the database's lower-case CHECK turns the sign-up into a 500.

**Test evidence:** `aDuplicateEmailIs409AnyCase` fails.

5CORS for every origin

"\*" lets any website's scripts call the API from a visitor's browser.

**Test evidence:** `theApiIsReachableOnlyFromHireloopsOwnWebApp` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class              | Fixed version | Flawed version |
|-------------------------|---------------|----------------|
| `CandidateDatabaseTest` | 2 / 2         | 2 / 2          |
| `CandidateContractTest` | 4 / 4         | 0 / 4          |
| `CandidateSecurityTest` | 5 / 5         | 3 / 5          |
| `FastHashTrapTest`      | 3 / 3         | 1 / 3          |

The database caught the weakest hash before it was stored. Without that CHECK, this pull request would have passed sign-up tests and quietly stored fast hashes.
