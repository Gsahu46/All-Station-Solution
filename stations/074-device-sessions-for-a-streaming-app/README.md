# Station 074 · Device sessions for a streaming app

Working Systems · 0–2 years · Core · Streaming · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · Spring Security 7 resource server · HS256 access tokens · rotating refresh tokens · JdbcClient · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Members and devices are demo data, not Streamo's. No video plays: "playback" is only a scope in the token. The signing key in application.yaml is a demo key.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 21 tests.

# 1 · Understand

## The problem in real life

1.  **A token on a shared laptop**

    Streamo's apps got a refresh token at sign-in that lasted a year and never changed. A copy taken from a shared laptop kept working.

2.  **The button that did nothing**

    The owner pressed "log out of all devices". It refreshed her screen; the copied token kept working for months.

3.  **The fix**

    Refresh tokens are swapped at every use and stored only as hashes. A used one shown again ends that device for everyone holding it. Each device can be removed, and its access token stops at once.

A secret that never changes can be copied once and used forever. Make every copy go stale.

## What are we building?

Sign-in per device, `POST /auth/refresh` that swaps the refresh token every time, `POST /auth/logout` for this device, and a device list where each device can be removed.

## An everyday analogy

A hotel key card that the desk re-codes every morning. Last night's card stops working. If someone shows up with last night's card, the desk knows a copy exists and cancels that room's cards, and the guest comes down for a new one.

## How it works in 4 steps

1.  **Sign in** on a device: a 10-minute access token and a 30-day refresh token. The table stores only the refresh token's hash.
2.  **Refresh**: the refresh token is used up in one database statement and a new one comes back.
3.  **Reuse**: a used-up token shown again ends the device: the thief's copy and the owner's new token both stop.
4.  **Remove** a device from the list: its refresh token stops, and its access token is refused on the next request.

Check yourself: a thief copies the refresh token and uses it before the owner does. Who is caught?

Both. The thief gets a new pair; then the owner's app sends the old token, which is now used up. That ends the device, so the thief's new token dies too, and the owner simply signs in again. The trap test `theThiefRefreshingFirstIsCaughtWhenTheOwnerRefreshes` shows it.

## What this station is not

- **No playback.** "playback" is only a scope; nothing streams.
- **No sign-in with Google or passkeys.** Those are stations 075 and 076.
- **Tokens are not tied to the device's hardware.** A copied token works until it is used twice or removed (see Practice, challenge 3).

## Key terms

| Term                | Simple meaning                                                                    | Everyday example                                                 | In this project            |
|---------------------|-----------------------------------------------------------------------------------|------------------------------------------------------------------|----------------------------|
| **Access token**    | A signed token that opens the API for 10 minutes.                                 | A day pass to a gym.                                             | `accessToken`, a JWT       |
| **Refresh token**   | A long random secret the app trades for a new access token, without the password. | The membership card you show to get today's day pass.            | `refreshToken`, 30 days    |
| **Rotation**        | Every refresh hands back a new refresh token; the old one is used up.             | A card that is swapped for a new one at every visit.             | `refresh_tokens.used_at`   |
| **Reuse detection** | A used-up refresh token shown again means two people have it: end the device.     | Two people with the same old card: both are stopped at the desk. | `revoked_reason = 'reuse'` |
| **Device session**  | One signed-in device: what the device list shows and what "remove" ends.          | One key on the key ring.                                         | `device_sessions`          |
| **Hash**            | A one-way fingerprint: the table holds it, never the token.                       | A fingerprint, not the finger.                                   | SHA-256 in `token_hash`    |

# 2 · Build: Spec

## Business problem

**Streamo** (a fictional streaming app): a stolen refresh token kept working for months, and "log out of all devices" did nothing.

## Acceptance criteria

Demo data: members anika and rohan. Demo rules: access tokens last 10 minutes, refresh tokens 30 days.

1.  **Given** a right email and password on a device, **then** `200` with an access token, a refresh token and the device id.
2.  **Given** a valid refresh token, **then** `200` with a new pair, and the old refresh token is used up.
3.  **Given** a used-up refresh token, **then** `401`, and that device is signed out for everyone.
4.  **Given** a device removed from the list or logged out, **then** its access and refresh tokens are refused at once.
5.  **Given** another member's device id, **then** `404`, the same as an unknown id, and nothing changes.
6.  **Given** a TV's token, **then** the device list is `403`: a TV in a living room may play, not manage the account.
7.  **Given** ten refreshes with one token at the same moment, **then** exactly one gets a new pair.

## Requirements

- Refresh tokens are 32 random bytes; only their SHA-256 is stored.
- At most one unused refresh token per device: the database enforces it.
- Unknown, expired, used and signed-out refresh tokens all get the same answer.

## Learning objectives

- Pair short access tokens with rotating refresh tokens.
- Detect reuse and end the device session.
- Make revocation immediate, and say what it costs.
- Put ownership into the query, and answer 404 for other people's things.

# 2 · Build: API contract

## Endpoints

| Method   | Path               | Purpose                                                                                                  |
|----------|--------------------|----------------------------------------------------------------------------------------------------------|
| `POST`   | `/auth/login`      | `{email, password, deviceName, deviceType}` (phone, tv or web); a new device session and its token pair. |
| `POST`   | `/auth/refresh`    | `{refreshToken}`; a new pair, the old refresh token used up.                                             |
| `POST`   | `/auth/logout`     | Bearer token; signs out this device only. `204`.                                                         |
| `GET`    | `/me/devices`      | This member's signed-in devices, oldest first; `current` marks the one asking. Scope `devices`.          |
| `DELETE` | `/me/devices/{id}` | Signs out one device. Scope `devices`. `204`.                                                            |

## Status codes

| Status    | When                                                                                                                                                |
|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| 200 / 204 | Tokens issued, list returned / device signed out                                                                                                    |
| 400       | A field missing or too long, an unknown device type, a refresh token of the wrong shape, a device id that is not a UUID                             |
| 401       | Wrong login; a refresh token that is unknown, expired, used or signed out; no access token, or one that fails a check or whose device is signed out |
| 403       | A TV's token on the device endpoints                                                                                                                |
| 404       | A device id that is unknown or another member's                                                                                                     |

## Captured examples

Captured with curl from the running app on 19 Oct 2026. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out. Each real token is replaced by a name, so you can follow which one was sent.

### Case 1: anika signs in on her phone

**Why:** a pair for this device, and its id.

Request

``` code
POST /auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "anika@example.com",
  "password": "anika-demo-pass",
  "deviceName": "Anika phone",
  "deviceType": "phone"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 463

{
  "accessToken": "<access token 1>",
  "refreshToken": "<refresh token 1>",
  "tokenType": "Bearer",
  "expiresIn": 600,
  "deviceId": "107cf393-3abd-4bd3-aa65-59be6defe51a"
}
```

### Case 2: and on the living-room TV

**Why:** a second device session.

Request

``` code
POST /auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "anika@example.com",
  "password": "anika-demo-pass",
  "deviceName": "Living room TV",
  "deviceType": "tv"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 453

{
  "accessToken": "<TV access token>",
  "refreshToken": "<TV refresh token>",
  "tokenType": "Bearer",
  "expiresIn": 600,
  "deviceId": "9c839a13-3232-4f35-9d20-8fb24cb08e68"
}
```

### Case 3: the phone refreshes

**Why:** refresh token 1 is used up; token 2 replaces it. The access token is the same text as in case 1: same member, device, scope and second, and signing the same claims with the same key gives the same token.

Request

``` code
POST /auth/refresh HTTP/1.1
Content-Type: application/json

{
  "refreshToken": "<refresh token 1>"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 463

{
  "accessToken": "<access token 1>",
  "refreshToken": "<refresh token 2>",
  "tokenType": "Bearer",
  "expiresIn": 600,
  "deviceId": "107cf393-3abd-4bd3-aa65-59be6defe51a"
}
```

### Case 4: the device list from the phone

**Why:** both devices; the phone is `current`.

Request

``` code
GET /me/devices HTTP/1.1
Authorization: Bearer <access token 1>
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 366

[
  {
    "id": "107cf393-3abd-4bd3-aa65-59be6defe51a",
    "name": "Anika phone",
    "type": "phone",
    "createdAt": "2026-10-19T12:44:00.650606Z",
    "lastUsedAt": "2026-10-19T12:44:00.843213Z",
    "current": true
  },
  {
    "id": "9c839a13-3232-4f35-9d20-8fb24cb08e68",
    "name": "Living room TV",
    "type": "tv",
    "createdAt": "2026-10-19T12:44:00.811623Z",
    "lastUsedAt": "2026-10-19T12:44:00.811663Z",
    "current": false
  }
]
```

### Case 5: the TV asks for the list

**Why:** `403`: its token has `playback` only.

Request

``` code
GET /me/devices HTTP/1.1
Authorization: Bearer <TV access token>
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 100

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This device cannot do this.",
  "instance": "/me/devices"
}
```

### Case 6: the phone removes the TV

**Why:** `204`.

Request

``` code
DELETE /me/devices/9c839a13-3232-4f35-9d20-8fb24cb08e68 HTTP/1.1
Authorization: Bearer <access token 1>
```

Response

``` code
HTTP/1.1 204
```

### Case 7: the TV's access token, right after

**Why:** `401` at once, not in 10 minutes.

Request

``` code
GET /me/devices HTTP/1.1
Authorization: Bearer <TV access token>
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Bearer
Content-Type: application/problem+json
Content-Length: 130

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid access token: sign in again to get one.",
  "instance": "/me/devices"
}
```

### Case 8: rohan tries to remove anika's phone

**Why:** `404`, as for an id that does not exist; the phone stays signed in.

Request

``` code
DELETE /me/devices/107cf393-3abd-4bd3-aa65-59be6defe51a HTTP/1.1
Authorization: Bearer <access token of rohan>
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such device",
  "instance": "/me/devices/107cf393-3abd-4bd3-aa65-59be6defe51a",
  "status": 404,
  "title": "Not Found"
}
```

### Case 9: refresh token 1 again, as a thief would

**Why:** used up: `401`, and the phone's session ends.

Request

``` code
POST /auth/refresh HTTP/1.1
Content-Type: application/json

{
  "refreshToken": "<refresh token 1>"
}
```

Response

``` code
HTTP/1.1 401 
Content-Type: application/problem+json

{
  "detail": "Sign in again on this device",
  "instance": "/auth/refresh",
  "status": 401,
  "title": "Unauthorized"
}
```

### Case 10: the phone's own new token

**Why:** also `401`: anika signs in again, and the thief's copy is dead for good.

Request

``` code
POST /auth/refresh HTTP/1.1
Content-Type: application/json

{
  "refreshToken": "<refresh token 2>"
}
```

Response

``` code
HTTP/1.1 401 
Content-Type: application/problem+json

{
  "detail": "Sign in again on this device",
  "instance": "/auth/refresh",
  "status": 401,
  "title": "Unauthorized"
}
```

## What the database holds afterwards

From `psql` in `docs/capture.sh`, after the requests above.

``` code
       email       |  device_name   | device_type | revoked_reason 
-------------------+----------------+-------------+----------------
 anika@example.com | Anika phone    | phone       | reuse
 anika@example.com | Living room TV | tv          | removed
 rohan@example.com | Rohan phone    | phone       | 
(3 rows)
```

``` code
     token_hash      |  device_name   | valid_for | used 
---------------------+----------------+-----------+------
 fb8e03983c9a2bb9... | Anika phone    | 30 days   | t
 61329891bdba9f1f... | Living room TV | 30 days   | f
 11e3154957e04e55... | Anika phone    | 30 days   | t
 88ac3925798c7940... | Rohan phone    | 30 days   | f
(4 rows)
```

The TV was removed (case 6) and the phone ended by reuse (case 9); Rohan's phone is untouched (case 8). Only hashes are stored (cut to 16 characters here). Both of the phone's tokens show as used: token 2 was used up by the attempt in case 10, although the device had already ended, so it got no new pair.

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                       | What happens                                                                | Proved by                                                                 |
|------------------------------------------------------------|-----------------------------------------------------------------------------|---------------------------------------------------------------------------|
| Login                                                      | A pair for this device: 600-second access token, 43-character refresh token | `loginGivesAShortAccessTokenAndARefreshTokenForThisDevice`                |
| Refresh                                                    | A new pair; one unused refresh token left; the chain goes on                | `refreshGivesANewPairAndTheOldRefreshTokenIsUsedUp`                       |
| The device list                                            | Active devices only, this one marked                                        | `theDeviceListShowsOnlyActiveDevicesAndMarksThisOne`                      |
| Logout                                                     | This device only                                                            | `logoutEndsThisDeviceOnly`                                                |
| Wrong password, unknown email, bad body                    | Identical `401`s; `400`                                                     | `wrongLoginsAre401AndBadBodiesAre400`                                     |
| Unknown device, not a UUID                                 | `404`; `400`                                                                | `anUnknownDeviceIs404AndABadIdIs400`                                      |
| No access token                                            | `401` with a Bearer challenge                                               | `noTokenIs401`                                                            |
| A TV's token on the device endpoints                       | `403`                                                                       | `aTvMayPlayButNotManageDevices`                                           |
| Another member's device                                    | `404`; that device stays signed in                                          | `anotherMembersDeviceIs404AndStaysSignedIn`                               |
| 10:20 and 10:31 old access token; 30-day-old refresh token | Accepted, then `401`; `401`                                                 | `accessTokensEndAfter10MinutesAndRefreshTokensAfter30Days`                |
| Ten refreshes with one token at once                       | Exactly one `200`; the device is ended for reuse                            | `tenParallelRefreshesWithOneTokenGiveOnePairAndEndTheDevice`              |
| Odd refresh tokens and headers                             | `400` or `401`, never an error                                              | `oddRefreshTokensAre400Or401NeverAnError`                                 |
| Rules written by plain SQL                                 | Refused by named constraints                                                | `refreshTokenRulesHoldWithoutJava`, `deviceAndMemberRulesHoldWithoutJava` |
| A rotation that fails half-way                             | Rolled back: the old token still works                                      | `aRotationThatFailsHalfWayLeavesTheOldTokenUsable`                        |
| A clock that moves between two reads                       | Still exactly 30 days stored                                                | `aClockThatMovesBetweenReadsStillStoresA30DayToken`                       |

## The trap

Plausible but wrong

Refresh tokens that never rotate, so a stolen one works for months.

- **The old store.** One token per sign-in, kept as it is, never replaced. The test copies it, presses the old "log out of all devices", and the copy still says "anika". The table holds the token itself.
- **Owner first.** On the real API, anika's app rotates; the thief's copy is now used up. Showing it ends the device: `401` for the thief and for anika's new token, and `revoked_reason` is `reuse`.
- **Thief first.** The thief rotates first and gets a pair. Then anika's app sends the old token: used up, so the device ends and the thief's new token dies too.
- **Remove means now.** The laptop removes the phone; one second later the phone's access token is `401`, not 10 minutes later.

While building, each part was undone once: a refresh token usable again (no `used_at` check) turned 3 tests red; no device end on reuse 3; no active-session check on access tokens 2; no member in the remove query 1; a TV given the devices scope 1; refresh without a transaction 2 (in the parallel test no refresh won at all: see Code).

``` code
package com.streamo.devices;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old design: one refresh token per sign-in, stored as it is, valid for a year, never replaced,
 * and a "log out of all devices" button that only cleared the app's screen. Then the same theft against the real API.
 */
class NeverRotatingTokenTrapTest extends ApiTest {

    /** The old token store, as it was: token text to member, nothing else. */
    static final class OldTokenStore {
        final Map<String, String> tokens = new HashMap<>();

        String signIn(String member) {
            String token = UUID.randomUUID().toString();
            tokens.put(token, member);
            return token;
        }

        String refresh(String token) {
            return tokens.get(token);   // the same token, every time, for a year
        }

        void logOutOfAllDevices(String member) {
            // the old button: a new access token on this screen, nothing removed from the store
        }
    }

    @Test
    void theOldTokenKeptWorkingForMonthsAfterItWasStolen() {
        OldTokenStore old = new OldTokenStore();
        String anikasToken = old.signIn("anika");
        String stolenCopy = anikasToken;              // copied off a shared laptop
        old.refresh(anikasToken);                     // anika keeps watching; her token never changes
        old.logOutOfAllDevices("anika");              // she notices and presses the button
        assertThat(old.refresh(stolenCopy)).isEqualTo("anika");   // months later, still anika
        assertThat(old.tokens).containsKey(anikasToken);          // and the table holds the token itself
    }

    @Test
    void aStolenRefreshTokenUsedAfterTheOwnerEndsTheWholeDevice() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        String stolenCopy = refresh(phone);
        JsonNode next = body(refreshRequest(refresh(phone)).andExpect(status().isOk()));   // anika's app rotates
        assertThat(refresh(next)).isNotEqualTo(stolenCopy);

        refreshRequest(stolenCopy).andExpect(status().isUnauthorized());   // the thief: a used token, a second holder
        assertThat(revokedReason(phone.get("deviceId").asString())).isEqualTo("reuse");
        refreshRequest(refresh(next)).andExpect(status().isUnauthorized());   // anika signs in again; the thief is out for good
        devices(access(next)).andExpect(status().isUnauthorized());
    }

    @Test
    void theThiefRefreshingFirstIsCaughtWhenTheOwnerRefreshes() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        JsonNode thief = body(refreshRequest(refresh(phone)).andExpect(status().isOk()));   // the thief is quicker
        refreshRequest(refresh(phone)).andExpect(status().isUnauthorized());               // anika's app: already used
        refreshRequest(refresh(thief)).andExpect(status().isUnauthorized());               // so the thief's new one dies too
    }

    @Test
    void removingADeviceStopsItsAccessTokenAtOnce() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        JsonNode laptop = login("anika", "Anika's laptop", "web");
        devices(access(phone)).andExpect(status().isOk());
        removeDevice(access(laptop), phone.get("deviceId").asString()).andExpect(status().isNoContent());
        later(Duration.ofSeconds(1));
        devices(access(phone)).andExpect(status().isUnauthorized());     // not in 10 minutes: now
        refreshRequest(refresh(phone)).andExpect(status().isUnauthorized());
        devices(access(laptop)).andExpect(status().isOk());
    }

    @Test
    void theDatabaseHoldsOnlyAHashOfEachRefreshToken() throws Exception {
        String token = refresh(login("anika", "Anika's phone", "phone"));
        assertThat(jdbc.sql("SELECT token_hash FROM refresh_tokens").query(String.class).single())
                .isEqualTo(Sessions.sha256(token)).isNotEqualTo(token);
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
./mvnw test                 # all 21 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Sign in, refresh twice with the same refresh token, and look at the device afterwards:

``` code
R=$(curl -s -X POST http://localhost:8080/auth/login -H 'Content-Type: application/json' \
  -d '{"email": "rohan@example.com", "password": "rohan-demo-pass", "deviceName": "My laptop", "deviceType": "web"}' \
  | sed 's/.*"refreshToken":"\([^"]*\)".*/\1/')
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8080/auth/refresh -H 'Content-Type: application/json' -d "{\"refreshToken\": \"$R\"}"
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8080/auth/refresh -H 'Content-Type: application/json' -d "{\"refreshToken\": \"$R\"}"
docker compose exec postgres psql -U streamo -d streamo -c "SELECT device_name, revoked_reason FROM device_sessions"
```

The first refresh prints 200, the second 401, and the laptop's row says `reuse`.

## Troubleshooting

| You see                                          | Cause                                                          | Fix                                                                                           |
|--------------------------------------------------|----------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| A removed device keeps working for minutes       | Access tokens checked only by signature and expiry.            | Check the device session on each request, as `JwtConfig` does, or accept the delay.           |
| Phones signed out after a timeout and retry      | The retry sent the already-used refresh token.                 | Expected with strict reuse detection; a short grace window or an idempotent retry softens it. |
| Every sign-in fails with `refresh_tokens_expiry` | Creation and expiry times from two clock reads.                | Read the clock once. Found while building this station.                                       |
| A `401` "Sign-in required" on a public endpoint  | A server error forwarded to `/error`, which the chain refused. | Permit `/error`, then read the real error in the log.                                         |
| `refresh_tokens_one_live_per_session` violated   | A new refresh token inserted before the old one was used up.   | Mark the old one used first, in the same transaction.                                         |
| `Could not find a valid Docker environment`      | Docker is not running.                                         | Start Docker Desktop or the Docker service.                                                   |

## Project layout

``` tree
stations/074-device-sessions-for-a-streaming-app/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/streamo/devices/
│   ├── SecurityConfig.java   ├── JwtConfig.java   ├── DeviceController.java
│   ├── Sessions.java   ├── TokenService.java   ├── ProblemResponses.java
│   └── DevicesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__members_devices_tokens.sql, V2__demo_members.sql
├── src/test/java/com/streamo/devices/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/streamo/devices/SecurityConfig.java`

Does  
Who may call what.

Why  
Login and refresh open (they check their own secrets); logout for any valid token; devices need scope `devices`; everything else refused; no session.

Without it  
A TV in a living room managing the account, or a new endpoint open by default.

`/error` is open: Spring forwards a server error there, and under `denyAll()` it came back as a `401` "Sign-in required" that hid the real `500`. Found while building.

CSRF is off because tokens travel in a header and a JSON body, never in a cookie a browser adds by itself. A web app that kept the refresh token in a cookie would need CSRF protection back.

#### `src/main/java/com/streamo/devices/JwtConfig.java`

Does  
The access-token checks, including "is this device still signed in?".

Why  
Signature (HS256 only), expiry with 30 seconds of allowance, issuer, audience, and one indexed lookup of the device session.

Without it  
A removed or logged-out device keeping access for the rest of its token's 10 minutes.

The lookup is a trade: one primary-key query per request buys immediate sign-out. Without it, "remove" works only for refresh tokens, and access tokens live on until they expire.

#### `src/main/java/com/streamo/devices/DeviceController.java`

Does  
The five endpoints and their input checks.

Why  
One `401` for every failed login and every failed refresh; a refresh token must have the shape of ours; another member's device is a `404`.

Without it  
Answers that tell an attacker which tokens or devices exist.

#### `src/main/java/com/streamo/devices/Sessions.java`

Does  
Sign-in, rotation, reuse detection, the device list.

Why  
The refresh token is used up by one `UPDATE ... WHERE used_at IS NULL ... RETURNING`: of parallel calls, exactly one gets the row. A used token shown again ends the device. The whole rotation is one transaction.

Without it  
Tokens that work twice, and a phone signed out by its own retry after a half-done rotation.

- The first run against the real app failed every sign-in: `created_at` and `expires_at` came from two clock reads, a few microseconds apart, so the token was 30 days and 1 microsecond long and `refresh_tokens_expiry` refused it. The tests had a clock that stood still. Now the clock is read once, and the test clock can move on every read. Found while building.
- Without `@Transactional` on `refresh`, the parallel test found no winner at all: the first statement committed alone, a losing call then saw a used token and ended the device before the winner had finished. Found while building.
- Ten parallel refreshes with one token end the device. That is the safe side of a race, and a real cost for a phone that retries after a timeout: a short grace window is the usual softening (not built here).
- An unknown email still pays for one bcrypt check, so it answers as slowly as a wrong password. No test measures the timing.

#### `src/main/java/com/streamo/devices/TokenService.java`

The 10-minute access token: `sub` the member, `sid` the device session, `scope` from the device type.

#### `src/main/java/com/streamo/devices/ProblemResponses.java`

401 (with `WWW-Authenticate: Bearer`) and 403 in the same problem JSON as every other error.

#### `src/main/resources/db/migration/V1__members_devices_tokens.sql`

Does  
Members, device sessions and refresh tokens, with their rules.

Why  
Only hashes; at most 30 days; at most one unused refresh token per device; a revoked device always has a reason.

Without it  
A script storing tokens in the clear, or two live tokens on one device.

#### `src/main/resources/db/migration/V2__demo_members.sql`

Two demo members with bcrypt hashes made by pgcrypto.

#### `src/main/resources/application.yaml`

Issuer, audience, lifetimes, allowance, and a demo key that real deployments take from a secret store.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/streamo/devices/DevicesApplication.java`

Entry point, and the `Clock` every time check uses.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                       | Result |
|---------------|-------------------------------------------------------------------|----------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `DeviceContractTest` (6)         | pass   |
| Every station | Reproduce the failure before the fix                              | `NeverRotatingTokenTrapTest` (5) | pass   |
| Database      | Rollback and constraint tests against a real database             | `DeviceDatabaseTest` (4)         | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `DeviceSecurityTest` (6)         | pass   |

The parallel test runs ten refreshes on virtual threads released by one latch, against the real PostgreSQL. The rollback test makes the database refuse new tokens with a trigger, so the failure happens inside the real transaction.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.streamo.devices.DeviceSecurityTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.streamo.devices.DeviceDatabaseTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.streamo.devices.DeviceContractTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.streamo.devices.NeverRotatingTokenTrapTest
[INFO] Tests run: 21, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/streamo/devices/NeverRotatingTokenTrapTest.java`

Written first: the old store keeps a stolen token alive; the real API ends the device on reuse, whoever came first; remove means now; only hashes are stored.

#### `src/test/java/com/streamo/devices/DeviceSecurityTest.java`

401, 403 for a TV, another member's device, expiry, ten parallel refreshes, odd input.

#### `src/test/java/com/streamo/devices/DeviceDatabaseTest.java`

Every named constraint with plain SQL, and a rotation that fails half-way.

#### `src/test/java/com/streamo/devices/DeviceContractTest.java`

Login, refresh, the device list, logout, wrong input, through HTTP.

#### `src/test/java/com/streamo/devices/ApiTest.java`

Shared setup: the test clock, a test key, no devices before each test, request helpers.

#### `src/test/java/com/streamo/devices/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/streamo/devices/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=SignOutOtherDevicesChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 21 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 24 tests pass (21 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Sign out every other device

The button that did nothing: `DELETE /me/devices` signs out all of this member's other devices at once (`204`) and keeps this one. A TV may not use it.

**Done when:** both tests in `SignOutOtherDevicesChallengeTest` pass.

Hints

- One `UPDATE` with `member_id = ? AND id <> ?`: the current device is the token's `sid`.
- The rule `/me/devices` already needs the `devices` scope.

#### `challenge/SignOutOtherDevicesChallengeTest.java`

``` code
package com.streamo.devices;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: the button that did nothing. DELETE /me/devices signs out every other device of this member at once
 * (204), keeps this one, and leaves other members alone. A TV may not press it (403).
 */
class SignOutOtherDevicesChallengeTest extends ApiTest {

    @Test
    void everyOtherDeviceIsSignedOutAtOnce() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        JsonNode tv = login("anika", "Living room TV", "tv");
        JsonNode laptop = login("anika", "Anika's laptop", "web");
        JsonNode rohan = login("rohan", "Rohan's phone", "phone");
        mvc.perform(delete("/me/devices").header("Authorization", "Bearer " + access(phone))).andExpect(status().isNoContent());
        devices(access(phone)).andExpect(jsonPath("$[*].name", contains("Anika's phone")));
        devices(access(laptop)).andExpect(status().isUnauthorized());
        refreshRequest(refresh(tv)).andExpect(status().isUnauthorized());
        refreshRequest(refresh(rohan)).andExpect(status().isOk());
    }

    @Test
    void aTvCannotSignOutTheOthers() throws Exception {
        JsonNode tv = login("anika", "Living room TV", "tv");
        mvc.perform(delete("/me/devices").header("Authorization", "Bearer " + access(tv))).andExpect(status().isForbidden());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## At most five devices

Demo rule: at most 5 signed-in devices per member. Signing in on a sixth signs out the one used longest ago, with `revoked_reason = 'limit'`.

**Done when:** the test in `DeviceLimitChallengeTest` passes.

Hints

- The database refuses the new reason until a V3 migration replaces `device_sessions_revoked_reason`.
- `ORDER BY last_used_at DESC OFFSET 4` finds the devices to sign out.
- Two sign-ins at the same moment could both count four: lock the member row first (`SELECT ... FOR UPDATE`).

#### `challenge/DeviceLimitChallengeTest.java`

``` code
package com.streamo.devices;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: demo rule, at most 5 signed-in devices per member. Signing in on a sixth signs out the one used
 * longest ago, with revoked_reason 'limit' (a new value the database must accept).
 */
class DeviceLimitChallengeTest extends ApiTest {

    @Test
    void aSixthDeviceSignsOutTheLeastRecentlyUsed() throws Exception {
        JsonNode first = login("anika", "Device 1", "web");
        for (int i = 2; i <= 5; i++) {
            later(Duration.ofMinutes(1));
            login("anika", "Device " + i, "web");
        }
        later(Duration.ofMinutes(1));
        JsonNode sixth = login("anika", "Device 6", "phone");
        devices(access(sixth)).andExpect(jsonPath("$", hasSize(5)));
        refreshRequest(refresh(first)).andExpect(status().isUnauthorized());
        assertThat(revokedReason(first.get("deviceId").asString())).isEqualTo("limit");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Retries, and tokens tied to the device

A phone on a train sends a refresh, the answer is lost, and it retries with the same token: today it is signed out. Design a grace window (how long, what the retry gets back, and why a thief inside the window is still caught later). Then read about DPoP (RFC 9449, Proposed Standard): tokens bound to a key that never leaves the device. What would a stolen copy be worth then?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: a stolen, never-changing token outlives "log out of all devices".
2.  Store device sessions and the hashes of their refresh tokens, with the rules as constraints.
3.  Rotate in one transaction: use up the old token with a conditional `UPDATE`, insert the new one.
4.  End the device on reuse; check the device on every access token.

## Design alternatives and trade-offs

| Approach                                                     | What it costs                                                             | Verdict                             |
|--------------------------------------------------------------|---------------------------------------------------------------------------|-------------------------------------|
| Rotation with reuse detection, device check on every request | One lookup per request; a retry after a lost answer signs the device out. | Chosen                              |
| One long refresh token, never rotated                        | A copy works until it expires.                                            | The trap                            |
| Rotation, no device check on access tokens                   | No lookup; a removed device keeps access for up to 10 minutes.            | Valid with very short access tokens |
| Rotation with a grace window for retries                     | Fewer accidental sign-outs; a thief inside the window gets in once.       | Common in practice                  |
| Sender-constrained tokens (DPoP, mTLS)                       | Keys on each device and proofs on each request.                           | Strongest; more moving parts        |

## Database design

| Object                                                   | What                                              | Why                                                |
|----------------------------------------------------------|---------------------------------------------------|----------------------------------------------------|
| `refresh_tokens_hash_shape`                              | CHECK: 64 hex characters                          | Only SHA-256 hashes, never the token.              |
| `refresh_tokens_expiry`                                  | CHECK: after creation, at most 30 days later      | No forever tokens from any writer.                 |
| `refresh_tokens_one_live_per_session`                    | Partial UNIQUE index on `session_id` where unused | Rotation as a rule: one live token per device.     |
| `device_sessions_revoked_with_reason`, `_revoked_reason` | CHECKs                                            | Every sign-out says why: logout, removed or reuse. |
| `device_sessions_type`, `_name_length`                   | CHECKs                                            | Only phone, tv and web; a name the list can show.  |

**Transaction boundary:** one refresh is one transaction: use up the old token, touch the device, insert the new token. A failure anywhere leaves the old token unused, so the retry works.

``` code
CREATE TABLE members (
    id            bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT members_pk PRIMARY KEY,
    email         text NOT NULL,
    password_hash text NOT NULL,
    CONSTRAINT members_email_lower CHECK (email = lower(email)),
    CONSTRAINT members_email_unique UNIQUE (email),
    CONSTRAINT members_password_hash_shape CHECK (password_hash ~ '^\{bcrypt\}\$2[aby]\$(1[0-9]|2[0-9]|3[01])\$[./A-Za-z0-9]{53}$')
);

-- One row per signed-in device. Revoking it ends the device's refresh tokens and, through the access-token check,
-- its access tokens at once.
CREATE TABLE device_sessions (
    id             uuid CONSTRAINT device_sessions_pk PRIMARY KEY,
    member_id      bigint NOT NULL CONSTRAINT device_sessions_member_fk REFERENCES members ON DELETE CASCADE,
    device_name    text NOT NULL,
    device_type    text NOT NULL,
    created_at     timestamptz NOT NULL,
    last_used_at   timestamptz NOT NULL,
    revoked_at     timestamptz,
    revoked_reason text,
    CONSTRAINT device_sessions_name_length CHECK (char_length(device_name) BETWEEN 1 AND 60),
    CONSTRAINT device_sessions_type CHECK (device_type IN ('phone', 'tv', 'web')),
    CONSTRAINT device_sessions_revoked_reason CHECK (revoked_reason IN ('logout', 'removed', 'reuse')),
    CONSTRAINT device_sessions_revoked_with_reason CHECK ((revoked_at IS NULL) = (revoked_reason IS NULL))
);
CREATE INDEX device_sessions_active_by_member ON device_sessions (member_id) WHERE revoked_at IS NULL;

-- Only the SHA-256 of each refresh token is stored. A used token stays, marked, so a second use is recognised.
CREATE TABLE refresh_tokens (
    token_hash char(64) CONSTRAINT refresh_tokens_pk PRIMARY KEY,
    session_id uuid NOT NULL CONSTRAINT refresh_tokens_session_fk REFERENCES device_sessions ON DELETE CASCADE,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    used_at    timestamptz,
    CONSTRAINT refresh_tokens_hash_shape CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT refresh_tokens_expiry CHECK (expires_at > created_at AND expires_at <= created_at + interval '30 days'),
    CONSTRAINT refresh_tokens_used_in_time CHECK (used_at IS NULL OR used_at >= created_at)
);
-- Rotation as a rule: a device has at most one refresh token that has not been used.
CREATE UNIQUE INDEX refresh_tokens_one_live_per_session ON refresh_tokens (session_id) WHERE used_at IS NULL;
```

# 3 · Go deeper: Production

Old rows  
Used and expired refresh tokens pile up. Keep used ones while their session could still be attacked (here at most 30 days), then delete them in a scheduled job.

Where apps keep the token  
Mobile apps: the platform's keychain or keystore. Browsers: an `HttpOnly`, `Secure`, `SameSite` cookie on the refresh path only, and then CSRF protection on that path.

Telling the member  
A reuse is a sign of theft: tell the member which device was signed out, and suggest a password change.

Logs  
Never log tokens or request bodies of the auth endpoints.

Standards  
The OAuth 2.0 Security Best Current Practice (RFC 9700, BCP 240) asks for refresh tokens that are rotated or bound to the client; refresh tokens themselves are in RFC 6749 (Proposed Standard).

# 3 · Go deeper: Interview

## Interview takeaways

Why have two tokens?

The access token is checked on every request without the database (or with one cheap lookup) and lives minutes. The refresh token is checked only on refresh, can be stored and revoked, and lives weeks.

What is refresh token rotation?

Each refresh hands back a new refresh token and marks the old one used. A stolen copy goes stale at the owner's next refresh.

What do you do when a used refresh token comes back?

Assume two holders and end the whole device session: the attacker's copy and the owner's latest token both stop; the owner signs in again.

Why store only a hash of refresh tokens?

A leaked table or backup then opens nothing. A fast hash such as SHA-256 is enough here because the token is 256 random bits, not a guessable password.

How do you make logout immediate with JWTs?

Check something server-side on each request, such as the device session or a revoke list, or keep access tokens so short that the delay is acceptable.

## Self-check rubric

| Area        | Meets the bar                          | Above the bar                                                      |
|-------------|----------------------------------------|--------------------------------------------------------------------|
| Correctness | All 21 tests pass.                     | You ran the flawed version and explained each failure.             |
| Rotation    | A new refresh token at every refresh.  | Reuse ends the device; parallel refreshes have exactly one winner. |
| Revocation  | Remove and logout stop refresh tokens. | Access tokens stop at once too, and you can say what that costs.   |
| Data        | Only hashes stored.                    | Rotation enforced by a partial unique index.                       |

# 3 · Go deeper: Review

## The pull request

A teammate fixes "members on trains keep getting signed out": the refresh token now stays the same for its 30 days, so a retry is harmless. They also drop the per-request device lookup ("tokens are signed, the database is busy"), and simplify device removal because "UUIDs cannot be guessed". Read the two files and list every problem before opening the findings.

#### `review/Sessions.java`

``` code
package com.streamo.devices;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.UUID;

/** Device sessions and their refresh tokens: sign-in, refresh, sign-out, the device list. */
@Service
class Sessions {

    record Issued(long memberId, UUID sessionId, String scope, String refreshToken) {
    }

    record Device(UUID id, String name, String type, OffsetDateTime createdAt, OffsetDateTime lastUsedAt) {
    }

    private static final SecureRandom RANDOM = new SecureRandom();

    private final JdbcClient jdbc;
    private final PasswordEncoder encoder;
    private final Clock clock;
    private final Duration refreshLifetime;
    private final String dummyHash;

    Sessions(JdbcClient jdbc, PasswordEncoder encoder, Clock clock, @Value("${streamo.refresh-lifetime}") Duration refreshLifetime) {
        this.jdbc = jdbc;
        this.encoder = encoder;
        this.clock = clock;
        this.refreshLifetime = refreshLifetime;
        this.dummyHash = encoder.encode("no-such-member");
    }

    /** A TV in a living room can play, but only a phone or a browser may see and remove devices. */
    static String scopeFor(String deviceType) {
        return deviceType.equals("tv") ? "playback" : "playback devices";
    }

    @Transactional
    Optional<Issued> signIn(String email, String password, String deviceName, String deviceType) {
        Optional<Member> member = jdbc.sql("SELECT id, password_hash FROM members WHERE email = ?")
                .param(email.strip().toLowerCase(Locale.ROOT)).query(Member.class).optional();
        // Unknown email: still pay for one bcrypt check, so the answer takes as long as a wrong password.
        boolean matches = encoder.matches(password, member.map(Member::passwordHash).orElse(dummyHash));
        if (member.isEmpty() || !matches) {
            return Optional.empty();
        }
        UUID session = UUID.randomUUID();
        jdbc.sql("INSERT INTO device_sessions (id, member_id, device_name, device_type, created_at, last_used_at) VALUES (?, ?, ?, ?, ?, ?)")
                .params(session, member.get().id(), deviceName.strip(), deviceType, now(), now()).update();
        return Optional.of(new Issued(member.get().id(), session, scopeFor(deviceType), newRefreshToken(session)));
    }

    /**
     * Gives a new access token for a valid refresh token. The refresh token itself stays the same, so a phone on a
     * flaky network that retries never signs itself out.
     */
    @Transactional
    Optional<Issued> refresh(String refreshToken) {
        Optional<UUID> session = jdbc.sql("SELECT session_id FROM refresh_tokens WHERE token_hash = ? AND expires_at > ?")
                .params(sha256(refreshToken), now()).query(UUID.class).optional();
        if (session.isEmpty()) {
            return Optional.empty();
        }
        Optional<ActiveSession> active = jdbc.sql("UPDATE device_sessions SET last_used_at = ? WHERE id = ? AND revoked_at IS NULL RETURNING member_id, device_type")
                .params(now(), session.get()).query(ActiveSession.class).optional();
        return active.map(a -> new Issued(a.memberId(), session.get(), scopeFor(a.deviceType()), refreshToken));
    }

    boolean isActive(String sessionId) {
        try {
            return sessionId != null && jdbc.sql("SELECT EXISTS (SELECT 1 FROM device_sessions WHERE id = ? AND revoked_at IS NULL)")
                    .param(UUID.fromString(sessionId)).query(Boolean.class).single();
        } catch (IllegalArgumentException notAUuid) {
            return false;
        }
    }

    List<Device> devices(long memberId) {
        return jdbc.sql("SELECT id, device_name AS name, device_type AS type, created_at, last_used_at FROM device_sessions WHERE member_id = ? AND revoked_at IS NULL ORDER BY created_at, id")
                .param(memberId).query(Device.class).list();
    }

    /** Device ids are random UUIDs: nobody can guess another member's. */
    boolean remove(long memberId, UUID deviceId, String reason) {
        return jdbc.sql("UPDATE device_sessions SET revoked_at = ?, revoked_reason = ? WHERE id = ? AND revoked_at IS NULL")
                .params(now(), reason, deviceId).update() == 1;
    }

    /** 32 random bytes for the device; only their SHA-256 is stored, so a copy of the table opens nothing. */
    private String newRefreshToken(UUID session) {
        byte[] bytes = new byte[32];
        RANDOM.nextBytes(bytes);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
        OffsetDateTime created = now();   // one clock read: two would put expiry a few microseconds past the 30-day CHECK
        jdbc.sql("INSERT INTO refresh_tokens (token_hash, session_id, created_at, expires_at) VALUES (?, ?, ?, ?)")
                .params(sha256(token), session, created, created.plus(refreshLifetime)).update();
        return token;
    }

    private OffsetDateTime now() {
        return OffsetDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
    }

    static String sha256(String token) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private record Member(long id, String passwordHash) {
    }

    private record ActiveSession(long memberId, String deviceType) {
    }
}
```

#### `review/JwtConfig.java`

``` code
package com.streamo.devices;

import com.nimbusds.jose.jwk.source.ImmutableSecret;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtClaimNames;
import org.springframework.security.oauth2.jwt.JwtClaimValidator;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtIssuerValidator;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.time.Clock;
import java.time.Duration;
import java.util.Base64;
import java.util.List;

/** Short-lived access tokens, signed with one shared key. Each names its device session. */
@Configuration
class JwtConfig {

    @Bean
    SecretKey jwtKey(@Value("${streamo.jwt.secret}") String secret) {
        return new SecretKeySpec(Base64.getUrlDecoder().decode(secret), "HmacSHA256");
    }

    @Bean
    JwtEncoder jwtEncoder(SecretKey key) {
        return new NimbusJwtEncoder(new ImmutableSecret<>(key));
    }

    /** Signature (HS256 only), expiry, issuer and audience: all local, so no database call on every request. */
    @Bean
    JwtDecoder jwtDecoder(SecretKey key, Clock clock, @Value("${streamo.jwt.issuer}") String issuer,
                          @Value("${streamo.jwt.audience}") String audience, @Value("${streamo.jwt.clock-skew}") Duration skew) {
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
        JwtTimestampValidator timestamps = new JwtTimestampValidator(skew);
        timestamps.setClock(clock);
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(timestamps, new JwtIssuerValidator(issuer),
                new JwtClaimValidator<List<String>>(JwtClaimNames.AUD, aud -> aud != null && aud.contains(audience))));
        return decoder;
    }
}
```

## Findings

1The refresh token is never replaced

"So a retry never signs a phone out" brings the original incident back: the same refresh token works for 30 days, a copy is never noticed, and two holders can refresh forever.

**Test evidence:** `refreshGivesANewPairAndTheOldRefreshTokenIsUsedUp`, `aStolenRefreshTokenUsedAfterTheOwnerEndsTheWholeDevice`, `theThiefRefreshingFirstIsCaughtWhenTheOwnerRefreshes` and `tenParallelRefreshesWithOneTokenGiveOnePairAndEndTheDevice` fail; `aRotationThatFailsHalfWayLeavesTheOldTokenUsable` fails too, because there is no rotation to fail.

2No device check on access tokens

"No database call on every request" saves one primary-key lookup, and a removed device keeps its access for up to 10 more minutes.

**Test evidence:** `removingADeviceStopsItsAccessTokenAtOnce` fails.

3Remove by id only

"UUIDs cannot be guessed" is not access control: ids appear in logs, screenshots and support tickets. Any member could sign out anyone's device.

**Test evidence:** `anotherMembersDeviceIs404AndStaysSignedIn` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class                   | Fixed version | Flawed version |
|------------------------------|---------------|----------------|
| `DeviceContractTest`         | 6 / 6         | 5 / 6          |
| `DeviceDatabaseTest`         | 4 / 4         | 3 / 4          |
| `DeviceSecurityTest`         | 6 / 6         | 4 / 6          |
| `NeverRotatingTokenTrapTest` | 5 / 5         | 2 / 5          |

The complaint was real: strict rotation does sign out a phone that retries. The fix for that is a short grace window, not a token that never changes.
