# Station 073 · Login with JWT for a fitness app

Working Systems · 0–2 years · Core · Fitness · Types: Security

Spring Boot 4.1.1 · Java 25 · Spring Security 7 OAuth2 resource server · Nimbus JOSE (HS256) · JwtEncoder / JwtDecoder · stateless. Needs JDK 25 (or 21, see Set up & code). No database and no Docker. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Members, passwords and workouts are demo data held in the app, not FitNest's. The signing key in application.yaml is a demo key; no identity provider is involved.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 16 tests.

# 1 · Understand

## The problem in real life

1.  **Logged out by a deploy**

    FitNest kept each login in the memory of the server that handled it. Every restart or deploy wiped it, and a member sent to another server was a stranger there.

2.  **A quick fix that was worse**

    The first token version only base64-decoded the token to read the member's name. Anyone could write a token saying "ravi" and read Ravi's workouts.

3.  **The fix**

    Signed tokens, checked on every request: the signature, the algorithm, the expiry with a small allowance, the issuer and the audience. Any server with the key can check them; none has to remember anything.

A token is only worth what the server checks. Reading it is not checking it.

## What are we building?

`POST /auth/login` swaps a username and password for a 15-minute signed token; `GET /workouts/me` returns the workouts of whoever the token is for.

## An everyday analogy

A festival wristband printed with your name, the festival, the day, and a hologram. Any gate can check it without phoning the ticket office. A wristband you drew yourself has no hologram; yesterday's has the wrong day.

## How it works in 4 steps

1.  **Login**: the password is checked against a bcrypt hash (station 071).
2.  **Issue**: the server writes the claims and signs them with the shared key.
3.  **Send**: the app sends `Authorization: Bearer <token>` with every request, to any server.
4.  **Check**: that server verifies signature, algorithm, expiry, issuer and audience, then the scope. Only then does the controller see `sub`.

Check yourself: the payload is only base64. Can a member change their own token to say they are someone else?

They can change the text, but the signature was computed over the original. The server recomputes it with the key, sees a mismatch and answers `401`. The security test does exactly this, and capture 4 shows the response.

## What this station is not

- **No refresh tokens or device list.** That is station 074.
- **No outside identity provider.** Sign-in with Google is station 075.
- **No logout yet.** A token stays valid until it expires; challenge 1 adds a revoke list.

## Key terms

| Term            | Simple meaning                                                                                                    | Everyday example                                                                  | In this project                     |
|-----------------|-------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|-------------------------------------|
| **Session**     | The server remembers "this browser is asha" in its own memory.                                                    | A cloakroom ticket that only one cloakroom knows.                                 | the old login                       |
| **JWT**         | Three base64url parts: header, payload (claims), signature. Anyone can read it; only the key holder can sign it.  | A sealed, signed pass: readable through the window, but the seal shows tampering. | `accessToken`                       |
| **Signature**   | A code computed from the header, payload and a secret key. Change one letter and it no longer matches.            | A wax seal.                                                                       | HS256 with the shared key           |
| **Claims**      | What the token says: who (sub), from whom (iss), for which API (aud), until when (exp), what they may do (scope). | The name, issuer and expiry date on a pass.                                       | `TokenService`                      |
| **Clock skew**  | A small allowance because two servers' clocks never agree exactly.                                                | A bus pass still accepted a minute after midnight.                                | 60 seconds                          |
| **401 and 403** | 401: we do not know who you are. 403: we know, and you may not do this.                                           | No ticket, against a ticket for another show.                                     | no token against no `workouts:read` |

# 2 · Build: Spec

## Business problem

**FitNest** (a fictional fitness app) logs members out on every deploy because sessions live in one server's memory.

## Acceptance criteria

Demo data: members asha, ravi and meera may read workouts; newbie has not finished onboarding and may not.

1.  **Given** a right username and password, **then** `200` with a Bearer token valid for 900 seconds.
2.  **Given** a wrong password or an unknown username, **then** the same `401`.
3.  **Given** a valid token, **then** `GET /workouts/me` returns that member's workouts, and nothing in the request chooses another member.
4.  **Given** no token, a changed, forged, unsigned or expired token, or one from another issuer or for another API, **then** `401` with `WWW-Authenticate: Bearer`.
5.  **Given** a valid token without `workouts:read`, **then** `403`.
6.  **Given** a token 15 minutes and 30 seconds old, **then** still accepted (60-second allowance); at 16 minutes and 1 second, refused.

## Requirements

- Tokens are HS256 only; the key is at least 256 bits and shared by every server.
- Tokens carry iss, sub, aud, iat, exp and scope, and nothing secret: anyone holding one can read it.
- No server-side session.

## Learning objectives

- Explain the three parts of a JWT and what the signature protects.
- Issue tokens with `JwtEncoder` and validate them with a resource server.
- Set expiry and clock skew, and test them with a controllable clock.
- Tell 401 from 403.

# 2 · Build: API contract

## Endpoints

| Method | Path           | Purpose                                                                                     |
|--------|----------------|---------------------------------------------------------------------------------------------|
| `POST` | `/auth/login`  | `{username, password}`; open to everyone; `200` with `{accessToken, tokenType, expiresIn}`. |
| `GET`  | `/workouts/me` | The token subject's workouts. Needs `Authorization: Bearer` and scope `workouts:read`.      |

## Status codes

| Status | When                                                                                      |
|--------|-------------------------------------------------------------------------------------------|
| 200    | Token issued / workouts returned                                                          |
| 400    | Username or password missing, empty or too long                                           |
| 401    | Wrong login (one answer for unknown and wrong); no token, or a token that fails any check |
| 403    | A valid token without `workouts:read`                                                     |

## Captured examples

Captured with curl from the running app on 19 Oct 2026. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out. Real tokens are replaced by their shape: each one opened an account for 15 minutes.

### Case 1: login

**Why:** a Bearer token for 900 seconds.

Request

``` code
POST /auth/login HTTP/1.1
Content-Type: application/json

{
  "username": "asha",
  "password": "asha-demo-pass"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 292

{
  "accessToken": "<header>.<payload>.<signature>",
  "tokenType": "Bearer",
  "expiresIn": 900
}
```

### Case 2: the token opens the member's own workouts

**Why:** "me" is the verified `sub`.

Request

``` code
GET /workouts/me HTTP/1.1
Authorization: Bearer <header>.<payload>.<signature>
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 135

{
  "member": "asha",
  "workouts": [
    {
      "date": "2026-10-17",
      "activity": "Run",
      "minutes": 35
    },
    {
      "date": "2026-10-18",
      "activity": "Yoga",
      "minutes": 50
    }
  ]
}
```

### Case 3: no token

**Why:** `401`, and `WWW-Authenticate: Bearer` says what is expected.

Request

``` code
GET /workouts/me HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Bearer
Content-Type: application/problem+json
Content-Length: 131

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid access token: sign in again to get one.",
  "instance": "/workouts/me"
}
```

### Case 4: asha's token with the payload changed to ravi

**Why:** the signature no longer matches: `401`. The old base64-only check would have shown Ravi's workouts.

Request

``` code
GET /workouts/me HTTP/1.1
Authorization: Bearer <header>.<payload with sub=ravi>.<signature of asha>
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Bearer
Content-Type: application/problem+json
Content-Length: 131

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid access token: sign in again to get one.",
  "instance": "/workouts/me"
}
```

### Case 5: a wrong password

**Why:** `401`, the same as for an unknown username.

Request

``` code
POST /auth/login HTTP/1.1
Content-Type: application/json

{
  "username": "asha",
  "password": "guess"
}
```

Response

``` code
HTTP/1.1 401 
Content-Type: application/problem+json

{
  "detail": "Wrong username or password",
  "instance": "/auth/login",
  "status": 401,
  "title": "Unauthorized"
}
```

### Case 6: a valid token for newbie, without the scope

**Why:** `403`: known, but not allowed.

Request

``` code
GET /workouts/me HTTP/1.1
Authorization: Bearer <token of newbie>
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 107

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This account cannot use this yet.",
  "instance": "/workouts/me"
}
```

## What the token says

The payload of asha's token from case 1, base64url-decoded by `docs/capture.sh`. Anyone with the token can read this; that is why it holds no secrets.

``` code
{"iss":"https://auth.fitnest.example","sub":"asha","aud":"fitnest-api","exp":1792413639,"iat":1792412739,"scope":"workouts:read"}
```

`exp` minus `iat` is 900 seconds. `scope` holds only the member's own grant: see "Found while building" in the Code tab.

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                             | What happens                                      | Proved by                                                     |
|------------------------------------------------------------------|---------------------------------------------------|---------------------------------------------------------------|
| Login, then workouts                                             | Token, then own workouts                          | `theTokenOpensTheMembersOwnWorkouts`                          |
| What the token says                                              | iss, sub, scope `workouts:read` only, 900 seconds | `thePayloadSaysWhoForWhichApiAndWhatTheyMayDo`                |
| A member with no workouts                                        | `200` with an empty list                          | `aMemberWithNoWorkoutsGetsAnEmptyList`                        |
| Wrong password, unknown user, bad body                           | Identical `401`s; `400`                           | `aWrongPasswordOrAnUnknownMemberIs401AndAMalformedLoginIs400` |
| No token                                                         | `401` with a Bearer challenge                     | `noTokenIs401WithABearerChallenge`                            |
| 15:30 old, then 16:01 old                                        | Accepted, then `401`                              | `aTokenExpiresAfter15MinutesWithOneMinuteForClockDifferences` |
| Signed with the right key, wrong iss or aud                      | `401`; all claims right is `200`                  | `aTokenFromAnotherIssuerOrForAnotherApiIs401`                 |
| Valid token, no scope                                            | `403`                                             | `aMemberWithoutTheScopeIs403`                                 |
| Payload changed to another member; `?member=ravi`                | `401`; the parameter is ignored                   | `changingWhoTheTokenIsForBreaksItsSignature`                  |
| Not a JWT, SQL-looking text, 5,000 characters, Basic credentials | `401`, never an error                             | `garbageInTheHeaderIs401NotAnError`                           |

## The trap

Plausible but wrong

Reading the token without checking it, and tokens that live for weeks.

- **Sessions in memory.** The test puts asha's session in one map and looks in a fresh one, as a restarted pod would: she is gone. A signed token checked on a second decoder with the same key still works.
- **A forged key.** A token signed with someone else's key says "ravi". The old base64-only read believes it; the API answers `401`.
- **No signature at all.** A token with `alg: none` and an empty signature. Believed by the old read; refused by the API, which accepts HS256 only.
- **Expired.** A month later the old read still says "asha"; the API answers `401`.

While building, each check was removed once: no audience check turned 1 test red; no issuer check 1; no clock allowance 1; the validator on the machine's clock instead of the app's 6; a 30-day lifetime 4; any signed-in member allowed 1; the scope built from all of the sign-in's authorities 1. Two changes turned nothing red and are explained in the Code tab.

``` code
package com.fitnest.workouts;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import tools.jackson.databind.JsonNode;

import javax.crypto.SecretKey;
import java.time.Duration;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. Two old designs: sessions kept in one server's memory (lost when the pod restarts), and the first
 * "JWT" fix that only base64-decoded the token to read who it was for. Then the same tokens against the real API.
 */
class UnverifiedTokenTrapTest extends ApiTest {

    @Autowired
    SecretKey jwtKey;

    /** The old fix: read the payload, trust it. No signature, no expiry, no issuer or audience. */
    static String oldReadSubject(String token) {
        JsonNode payload = JSON.readTree(new String(Base64.getUrlDecoder().decode(token.split("\\.")[1])));
        return payload.get("sub").asString();
    }

    @Test
    void sessionsInOnePodsMemoryAreLostWhenItRestarts() {
        Map<String, String> podMemory = new HashMap<>();   // the old login stored "session id -> member" here
        String session = UUID.randomUUID().toString();
        podMemory.put(session, "asha");
        Map<String, String> afterRestart = new HashMap<>();   // a restarted (or different) pod starts empty
        assertThat(afterRestart.get(session)).isNull();      // asha is logged out
    }

    @Test
    void aSignedTokenWorksOnAnyPodWithTheSameKey() throws Exception {
        String token = login("asha", "asha-demo-pass");
        // Another pod: a decoder built from the shared key, with nothing remembered about the login.
        NimbusJwtDecoder anotherPod = NimbusJwtDecoder.withSecretKey(jwtKey).macAlgorithm(MacAlgorithm.HS256).build();
        JwtTimestampValidator expiry = new JwtTimestampValidator();
        expiry.setClock(clock);   // the test clock, not the machine's
        anotherPod.setJwtValidator(expiry);
        assertThat(anotherPod.decode(token).getSubject()).isEqualTo("asha");
    }

    @Test
    void readingWithoutVerifyingTrustsAForgedToken() throws Exception {
        String forged = forge("someone-elses-key-that-is-at-least-256-bits".getBytes(), "ravi", "https://auth.fitnest.example", "fitnest-api", START.plusSeconds(900));
        assertThat(oldReadSubject(forged)).isEqualTo("ravi");   // the old code would show ravi's workouts
        workouts(forged).andExpect(status().isUnauthorized());
    }

    @Test
    void readingWithoutVerifyingTrustsAnUnsignedToken() throws Exception {
        String unsigned = b64("{\"alg\":\"none\"}") + "." + b64("{\"sub\":\"ravi\",\"iss\":\"https://auth.fitnest.example\",\"aud\":\"fitnest-api\",\"scope\":\"workouts:read\",\"exp\":9999999999}") + ".";
        assertThat(oldReadSubject(unsigned)).isEqualTo("ravi");
        workouts(unsigned).andExpect(status().isUnauthorized());
    }

    @Test
    void readingWithoutVerifyingTrustsAnExpiredToken() throws Exception {
        String token = login("asha", "asha-demo-pass");
        later(Duration.ofDays(30));
        assertThat(oldReadSubject(token)).isEqualTo("asha");   // a month later, still "asha" to the old code
        workouts(token).andExpect(status().isUnauthorized());
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Docker   | Not needed: no database in this station         |                 |
| Maven    | Not needed: the project ships the Maven wrapper |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 16 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Log in, keep the token, use it, then decode its payload and read the claims:

``` code
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login -H 'Content-Type: application/json' \
  -d '{"username": "asha", "password": "asha-demo-pass"}' | sed 's/.*"accessToken":"\([^"]*\)".*/\1/')
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/workouts/me
echo "$TOKEN" | cut -d. -f2 | tr '_-' '/+' | base64 -d 2>/dev/null; echo
```

Restart the app and send the same token: it still works, because nothing was remembered. Change the key in `application.yaml` and restart: now it does not.

## Troubleshooting

| You see                                         | Cause                                            | Fix                                                                            |
|-------------------------------------------------|--------------------------------------------------|--------------------------------------------------------------------------------|
| Every token is `401` right after login          | Servers with different keys, or a clock far off. | Every pod needs the same key; keep clocks in sync (NTP).                       |
| `Jwt expired at …` in a test, for a fresh token | A decoder built without the app's clock.         | Call `setClock` on the timestamp validator. Found while building this station. |
| `FACTOR_PASSWORD` in a token's scope            | Spring Security 7 adds it to a password sign-in. | Build the scope from the member's own grants.                                  |
| `403` on a new endpoint                         | `denyAll()` at the end of the chain.             | Add a rule for the path, on purpose.                                           |

## Project layout

``` tree
stations/073-login-with-jwt-for-a-fitness-app/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/fitnest/workouts/
│   ├── SecurityConfig.java   ├── JwtConfig.java   ├── TokenService.java
│   ├── AuthController.java   ├── ProblemResponses.java   └── WorkoutsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/fitnest/workouts/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/fitnest/workouts/SecurityConfig.java`

Does  
The filter chain, the demo members and the login's authentication manager.

Why  
Login open; workouts need `SCOPE_workouts:read`; everything else refused; the resource server checks every bearer token; no session.

Without it  
An endpoint added later and open to everyone by default, or a valid token treated as permission for everything.

- CSRF is off because the token travels in a header the browser never adds on its own. If the token moved into a cookie, CSRF protection must come back.
- `denyAll()` at the end: a new path is refused until someone decides who may use it.
- Changing STATELESS to IF_REQUIRED turned no test red: the bearer filter never puts the sign-in into a session. The line stays, to say what the API is.

#### `src/main/java/com/fitnest/workouts/JwtConfig.java`

Does  
The key, the encoder and the decoder with its five checks.

Why  
Signature with the shared key and HS256 only; exp and nbf with 60 seconds of allowance, on the app's clock; issuer; audience.

Without it  
Forged, unsigned, expired or misdirected tokens being accepted.

- Removing `.macAlgorithm(HS256)` turned no test red: it is already the default for `withSecretKey`. It stays, so the choice is written down.
- The timestamp validator uses the machine's clock unless given one: a second decoder in a test, built without it, refused a fresh token. Found while building.

#### `src/main/java/com/fitnest/workouts/TokenService.java`

Does  
Writes the claims and signs them.

Why  
15-minute tokens with iss, sub, aud, iat, exp and the member's grants as scope.

Without it  
Tokens that live for weeks, or carry more than they should.

Spring Security 7 adds a `FACTOR_PASSWORD` authority to a password sign-in. Built from `authentication.getAuthorities()`, every token's scope said `workouts:read FACTOR_PASSWORD`. The scope now comes from the member's own grants. Found while building.

#### `src/main/java/com/fitnest/workouts/AuthController.java`

Does  
Login and "my workouts".

Why  
One `401` for every failed login; "me" is the verified token subject.

Without it  
A member chosen by a parameter, or login answers that reveal which usernames exist.

#### `src/main/java/com/fitnest/workouts/ProblemResponses.java`

401 (with `WWW-Authenticate: Bearer`) and 403 in the same problem JSON as every other error.

#### `src/main/resources/application.yaml`

Issuer, audience, lifetime, allowance, and a demo key that real deployments take from a secret store.

#### `src/main/java/com/fitnest/workouts/WorkoutsApplication.java`

Entry point, and the `Clock` every time check uses.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                    | Result |
|---------------|-------------------------------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `WorkoutContractTest` (5)     | pass   |
| Every station | Reproduce the failure before the fix                              | `UnverifiedTokenTrapTest` (5) | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `WorkoutSecurityTest` (6)     | pass   |

"Not found" here is the unknown username, answered like a wrong password on purpose, and the member with no workouts. "Another user's data": the only way to ask for Ravi's workouts is to change the token, which breaks its signature, or add a parameter, which is ignored.

Time is controlled: the app's `Clock` is a test clock, so "16 minutes later" takes no time and never depends on the machine.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1. No Docker needed. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.fitnest.workouts.WorkoutSecurityTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.fitnest.workouts.UnverifiedTokenTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.fitnest.workouts.WorkoutContractTest
[INFO] Tests run: 16, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/fitnest/workouts/UnverifiedTokenTrapTest.java`

Written first: sessions lost on restart, then a forged, an unsigned and an expired token, believed by the old read and refused by the API.

#### `src/test/java/com/fitnest/workouts/WorkoutSecurityTest.java`

401 with a challenge, expiry with allowance, issuer and audience, 403, a changed payload, garbage headers.

#### `src/test/java/com/fitnest/workouts/WorkoutContractTest.java`

Login and workouts through HTTP, and what the token says.

#### `src/test/java/com/fitnest/workouts/ApiTest.java`

Shared setup: the test clock, a test key, login helpers, and `forge` to build tokens the way an attacker would.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/fitnest/workouts/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=LogoutRevokesTokenChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 16 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 20 tests pass (16 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 30 minutes

## Logout that revokes one token

Add `POST /auth/logout` with the bearer token: `204`, and that token is `401` from then on, while a new login works.

**Done when:** both tests in `LogoutRevokesTokenChallengeTest` pass.

Hints

- Give every token an id: `.id(UUID.randomUUID().toString())` sets the `jti` claim.
- Keep revoked ids with their expiry, and forget them once the token would have expired anyway.
- Add a validator to the decoder that fails for a revoked id. `JwtClaimValidator` also fails when the claim is missing, so write a plain one.

#### `challenge/LogoutRevokesTokenChallengeTest.java`

``` code
package com.fitnest.workouts;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /auth/logout with the token makes that one token stop working at once (204), on every pod
 * that shares the revoked list, while a fresh login still works. A revoked id only needs keeping until the token
 * would have expired anyway.
 */
class LogoutRevokesTokenChallengeTest extends ApiTest {

    @Test
    void aLoggedOutTokenIsRefusedButANewLoginWorks() throws Exception {
        String token = login("asha", "asha-demo-pass");
        workouts(token).andExpect(status().isOk());
        mvc.perform(post("/auth/logout").header("Authorization", "Bearer " + token)).andExpect(status().isNoContent());
        workouts(token).andExpect(status().isUnauthorized());
        later(Duration.ofSeconds(1));
        workouts(login("asha", "asha-demo-pass")).andExpect(status().isOk());
    }

    @Test
    void logoutNeedsAValidToken() throws Exception {
        mvc.perform(post("/auth/logout")).andExpect(status().isUnauthorized());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## A coach reads their trainees' workouts

Add coach kabir (scope `coach:read`) and `GET /workouts/{member}`: `200` for his trainees (demo rule: asha), `403` for anyone else, and `403` for members without the scope.

**Done when:** both tests in `CoachReadsTraineesChallengeTest` pass.

Hints

- The scope says "is a coach"; it does not say "of whom". Check the trainee list too.
- A rule for `/workouts/*` in the filter chain; `/workouts/me` keeps its own rule, which comes first.

#### `challenge/CoachReadsTraineesChallengeTest.java`

``` code
package com.fitnest.workouts;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: coach kabir (password "kabir-demo-pass", scope coach:read) reads GET /workouts/{member} for his
 * trainees only (demo rule: asha). Another member is 403; a member without coach:read is 403 even for themselves.
 */
class CoachReadsTraineesChallengeTest extends ApiTest {

    String token;

    @Test
    void aCoachReadsOnlyTheirOwnTrainees() throws Exception {
        token = login("kabir", "kabir-demo-pass");
        mvc.perform(get("/workouts/asha").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk()).andExpect(jsonPath("$.member").value("asha")).andExpect(jsonPath("$.workouts.length()").value(2));
        mvc.perform(get("/workouts/ravi").header("Authorization", "Bearer " + token)).andExpect(status().isForbidden());
    }

    @Test
    void aMemberIsNotACoach() throws Exception {
        token = login("ravi", "ravi-demo-pass");
        mvc.perform(get("/workouts/ravi").header("Authorization", "Bearer " + token)).andExpect(status().isForbidden());
        mvc.perform(get("/workouts/asha")).andExpect(status().isUnauthorized());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Refresh tokens and a new signing key

Members should not log in every 15 minutes, and the key must be replaced one day without logging everyone out. Design a refresh token (where it is stored, how it is rotated and revoked) and a key change with a `kid` header, where for a while both keys verify and only the new one signs. When would you move from one shared key (HS256) to a private key that signs and public keys that verify (RS256 or ES256)?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: sessions lost on restart, then three tokens the base64-only read believes.
2.  Issue tokens with Spring Security's `JwtEncoder` after a normal password check.
3.  Validate with the OAuth2 resource server: one decoder with every check, on the app's clock.
4.  Authorise by scope, and refuse every path not listed.

## Design alternatives and trade-offs

| Approach                                                | What it costs                                                  | Verdict                         |
|---------------------------------------------------------|----------------------------------------------------------------|---------------------------------|
| Signed 15-minute JWT, HS256, shared key                 | No logout before expiry; every server holds the signing key.   | Chosen                          |
| Base64-decode the token and trust it                    | Anyone can write any member's name.                            | The trap                        |
| Sessions in each server's memory                        | Lost on every restart; sticky routing needed.                  | The old problem                 |
| Sessions in a shared store (Spring Session with Valkey) | Logout is easy; every request reads the store.                 | Valid, especially for browsers  |
| RS256 or ES256: a private key signs, public keys verify | Key pairs and a key set to publish; only the issuer can sign.  | When other services verify      |
| Opaque tokens with introspection                        | A call to the issuer per request (or a cache); instant revoke. | When revocation must be instant |

## Database design

No database in this station: the point is that the API keeps no login state. Members and workouts are demo data in the app. Stations 074 and 076 store sessions and passkeys in PostgreSQL, with their constraints.

# 3 · Go deeper: Production

The key  
Anyone with the HS256 key can sign tokens for any member. Keep it in a secret store, at least 256 bits, never in the repository (the one here is a demo key), and plan how to replace it.

Revocation  
A stolen token works until it expires. Short lifetimes limit the damage; a revoke list (challenge 1) or refresh tokens (station 074) cover the rest.

Clocks  
Expiry depends on every server's clock. Keep them in sync (NTP) and the allowance small.

Logs  
Never log the `Authorization` header or tokens: each one is a key to an account until it expires.

Standards  
JWT is RFC 7519 and JWS is RFC 7515 (both Proposed Standards); RFC 8725 (Best Current Practice, BCP 225) lists what to check; bearer tokens over HTTP are RFC 6750 (Proposed Standard).

# 3 · Go deeper: Interview

## Interview takeaways

Is a JWT encrypted?

Usually not. A signed JWT (JWS) is only base64url-encoded: anyone can read the claims. The signature stops changes, not reading. Put nothing secret in it.

What must a server check on every token?

The signature with the expected key, an allowed algorithm (never "none"), exp and nbf with a small allowance, the issuer and the audience. Then the scopes for the endpoint.

401 or 403?

401 when the caller is not authenticated (no token, or one that fails a check), with WWW-Authenticate. 403 when the token is valid but does not grant this.

How do you log out a JWT?

You cannot change a token already issued. Keep lifetimes short, keep a revoke list of token ids until they expire, or use refresh tokens that can be revoked.

HS256 or RS256?

HS256: one shared secret signs and verifies, fine when one team runs every server. RS256 or ES256: only the issuer holds the private key, and anyone can verify with the public key.

## Self-check rubric

| Area          | Meets the bar                            | Above the bar                                                             |
|---------------|------------------------------------------|---------------------------------------------------------------------------|
| Correctness   | All 16 tests pass.                       | You ran the flawed version and explained each failure.                    |
| Validation    | Signature, algorithm and expiry checked. | Issuer, audience and clock allowance too, tested with a controlled clock. |
| Authorization | 401 and 403 used correctly.              | Scopes kept to the member's own grants.                                   |
| Operations    | The key is not in code.                  | A plan to revoke tokens and replace the key.                              |

# 3 · Go deeper: Review

## The pull request

A teammate simplifies the token setup: "we only accept our own tokens, so issuer and audience checks are noise". Members complained about logging in, so tokens now last 30 days, and the workouts rule is now just "signed in". Read the three files and list every problem before opening the findings.

#### `review/JwtConfig.java`

``` code
package com.fitnest.workouts;

import com.nimbusds.jose.jwk.source.ImmutableSecret;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.time.Clock;
import java.time.Duration;
import java.util.Base64;

/** One HMAC key signs tokens and checks them. Every pod has the same key, so any pod accepts any pod's token. */
@Configuration
class JwtConfig {

    @Bean
    SecretKey jwtKey(@Value("${fitnest.jwt.secret}") String secret) {
        return new SecretKeySpec(Base64.getUrlDecoder().decode(secret), "HmacSHA256");
    }

    @Bean
    JwtEncoder jwtEncoder(SecretKey key) {
        return new NimbusJwtEncoder(new ImmutableSecret<>(key));
    }

    /** Checks the signature and the expiry. Our own tokens only, so issuer and audience add nothing. */
    @Bean
    JwtDecoder jwtDecoder(SecretKey key, Clock clock, @Value("${fitnest.jwt.issuer}") String issuer,
                          @Value("${fitnest.jwt.audience}") String audience, @Value("${fitnest.jwt.clock-skew}") Duration skew) {
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
        JwtTimestampValidator timestamps = new JwtTimestampValidator(skew);
        timestamps.setClock(clock);
        decoder.setJwtValidator(timestamps);
        return decoder;
    }
}
```

#### `review/TokenService.java`

``` code
package com.fitnest.workouts;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.stream.Collectors;

/** Issues short-lived access tokens: who (sub), for which API (aud), from whom (iss), what they may do (scope), until when (exp). */
@Service
class TokenService {

    record AccessToken(String accessToken, String tokenType, long expiresIn) {
    }

    private final JwtEncoder encoder;
    private final Clock clock;
    private final String issuer;
    private final String audience;
    private final Duration lifetime;

    TokenService(JwtEncoder encoder, Clock clock, @Value("${fitnest.jwt.issuer}") String issuer,
                 @Value("${fitnest.jwt.audience}") String audience, @Value("${fitnest.jwt.lifetime}") Duration lifetime) {
        this.encoder = encoder;
        this.clock = clock;
        this.issuer = issuer;
        this.audience = audience;
        this.lifetime = lifetime;
    }

    AccessToken issue(Authentication user) {
        Instant now = clock.instant();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(issuer).subject(user.getName()).audience(java.util.List.of(audience))
                .issuedAt(now).expiresAt(now.plus(Duration.ofDays(30)))   // members hated logging in again
                .claim("scope", ((UserDetails) user.getPrincipal()).getAuthorities().stream()   // the member's grants; user.getAuthorities() also has FACTOR_PASSWORD (Spring Security 7)
                        .map(GrantedAuthority::getAuthority).collect(Collectors.joining(" ")))
                .build();
        String token = encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue();
        return new AccessToken(token, "Bearer", Duration.ofDays(30).toSeconds());
    }
}
```

#### `review/SecurityConfig.java`

``` code
package com.fitnest.workouts;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.ProviderManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
class SecurityConfig {

    /** Login is open; workouts need a valid token that carries the workouts:read scope. No server-side session at all. */
    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.POST, "/auth/login").permitAll()
                        .requestMatchers(HttpMethod.GET, "/workouts/me").authenticated()
                        .anyRequest().denyAll())
                .oauth2ResourceServer(o -> o.jwt(jwt -> {}).authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // the token travels in a header the browser never adds by itself
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    /** Demo members, bcrypt hashes. Authorities become the token's scopes. meera has logged no workouts yet; newbie has not finished onboarding, so may not read workouts. */
    @Bean
    UserDetailsService users(PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(
                User.withUsername("asha").password(encoder.encode("asha-demo-pass")).authorities("workouts:read").build(),
                User.withUsername("ravi").password(encoder.encode("ravi-demo-pass")).authorities("workouts:read").build(),
                User.withUsername("meera").password(encoder.encode("meera-demo-pass")).authorities("workouts:read").build(),
                User.withUsername("newbie").password(encoder.encode("newbie-demo-pass")).authorities("profile:read").build());
    }

    @Bean
    AuthenticationManager authenticationManager(UserDetailsService users, PasswordEncoder encoder) {
        DaoAuthenticationProvider provider = new DaoAuthenticationProvider(users);
        provider.setPasswordEncoder(encoder);
        return new ProviderManager(provider);
    }
}
```

## Findings

1No issuer or audience check

"Our own tokens only" is the assumption that breaks: a token signed with the same key for another FitNest API, or by another issuer sharing the key, is accepted here.

**Test evidence:** `aTokenFromAnotherIssuerOrForAnotherApiIs401` fails.

230-day tokens

Members hate logging in, but a stolen token now opens the account for a month, and there is no way to take it back.

**Test evidence:** `loginGivesAShortLivedBearerToken`, `thePayloadSaysWhoForWhichApiAndWhatTheyMayDo`, `aTokenExpiresAfter15MinutesWithOneMinuteForClockDifferences` and `readingWithoutVerifyingTrustsAnExpiredToken` fail.

3Any signed-in member reads workouts

`authenticated()` instead of the scope: newbie, who may not read workouts yet, gets them. A valid token is identity, not permission.

**Test evidence:** `aMemberWithoutTheScopeIs403` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the three flawed files copied over the real ones, then the full suite run.

| Test class                | Fixed version | Flawed version |
|---------------------------|---------------|----------------|
| `UnverifiedTokenTrapTest` | 5 / 5         | 4 / 5          |
| `WorkoutContractTest`     | 5 / 5         | 3 / 5          |
| `WorkoutSecurityTest`     | 6 / 6         | 3 / 6          |

Every flaw here still lets the normal login and workouts work. Only tests that try the wrong token, the old token and the wrong member catch them.
