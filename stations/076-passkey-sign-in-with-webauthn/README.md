# Station 076 · Passkey sign-in with WebAuthn

Working Systems · 0–2 years · Core · Fintech · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · WebAuthn with webauthn4j 0.31.9 · TOTP (RFC 6238) · Spring Security 7 resource server · JdbcClient · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows). A real passkey in a browser needs HTTPS on the configured origin.

**Simulation:** Customers and balances are demo rows in a table, not Tijori's; no bank is involved. In the tests, webauthn4j's emulator plays the phone's authenticator and browser, with real keys and real signatures. The TOTP secret is RFC 6238's published test secret, demo only.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 22 tests.

# 1 · Understand

## The problem in real life

1.  **Phished and SIM-swapped**

    Fake Tijori pages collected passwords, and attackers moved customers' numbers to new SIM cards to receive their SMS codes. Fourteen accounts were drained.

2.  **Passkeys, half done**

    The first passkey code only checked the signature. A sign-in recorded once could be sent again, and an answer made for a look-alike page was accepted.

3.  **The fix**

    Every sign-in signs a fresh challenge from Tijori, on Tijori's page, for Tijori's domain, with the customer's fingerprint or face. The server checks all of it. The fallback is a password with an authenticator-app code, never SMS.

A signature only proves the key signed something. What it signed, and for whom, is the server's to check.

## What are we building?

Passkey registration and sign-in (two ceremonies, each with options and an answer), a password-plus-code fallback, and an account page.

## An everyday analogy

A notary stamps a letter only after reading today's date and the addressee aloud. A stamped letter dated last week, or addressed to the shop next door, is worth nothing here, however real the stamp.

## How it works in 4 steps

1.  **Options**: Tijori sends a fresh challenge and its domain.
2.  **Phone**: the customer touches the sensor; the phone signs the challenge together with the page's origin and the domain.
3.  **Check**: Tijori uses up the challenge, then checks origin, domain, fingerprint flag, signature and counter.
4.  **Token**: a 10-minute access token that records how the customer signed in.

Check yourself: why can a fake page not simply pass the customer's passkey answer on to Tijori?

The answer names the page that asked it, inside the signed data. Tijori accepts only its own origin, so an answer made on `tijori-login.example` is refused, as `aSignInAnsweredForAPhishingPageIsRefused` shows. (Real browsers also refuse to use a Tijori passkey on another domain at all.)

## What this station is not

- **No real phone in the tests.** webauthn4j's emulator plays it, with real keys.
- **No attestation checks.** Tijori does not ask which model of authenticator made the key (`attestation: none`).
- **No account recovery.** Losing every passkey and the code app is a support process (Practice, challenge 3).

## Key terms

| Term                      | Simple meaning                                                                                                       | Everyday example                             | In this project              |
|---------------------------|----------------------------------------------------------------------------------------------------------------------|----------------------------------------------|------------------------------|
| **Passkey**               | A key pair made by the phone for one website. The private key never leaves the phone; the site keeps the public key. | A house key cut for one door only.           | `passkeys` table             |
| **Relying party (RP) id** | The website domain a passkey belongs to. The phone will not use it for another domain.                               | The address engraved on the key.             | `tijori.example`             |
| **Challenge**             | Random bytes the server sends for one sign-in; the phone signs them.                                                 | A one-time password the guard says out loud. | `webauthn_challenges`        |
| **Origin**                | The exact web address of the page that asked the phone, written into what it signs.                                  | The return address on a letter.              | `https://app.tijori.example` |
| **User verification**     | The phone checked a fingerprint, face or PIN before signing.                                                         | The guard checks the face matches the badge. | `userVerification: required` |
| **TOTP**                  | A six-digit code from an app, made from a shared secret and the time, new every 30 seconds.                          | A safe whose code changes every half minute. | `POST /2fa/totp`             |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional bank) lost 14 accounts to phished passwords and SIM-swapped SMS codes; customers want to sign in with a fingerprint or face.

## Acceptance criteria

Demo data: customers zoya and dev, with passwords and the same demo TOTP secret.

1.  **Given** the right password and the current code, **then** `200` with a token; the same code again is `401`.
2.  **Given** a sign-in from the last 5 minutes, **then** a passkey can be registered; with an older token, `403`.
3.  **Given** a registered passkey and a fresh challenge on Tijori's page, **then** sign-in works without a password.
4.  **Given** a sign-in answer sent twice, made for another page, or made for another domain, **then** it is refused.
5.  **Given** a passkey answer claiming another customer, or a registration on another customer's challenge, **then** refused.
6.  **Given** ten sign-ins with one code at once, **then** exactly one token.

## Requirements

- The challenge, origin and RP id come from the server, never from the request.
- Challenges are single-use and last 5 minutes; the database enforces their shape and lifetime.
- No SMS anywhere. A password is never enough on its own.

## Learning objectives

- Run both WebAuthn ceremonies and name every server-side check.
- Explain what makes passkeys resistant to phishing, and what the server still has to do.
- Implement TOTP with single use and a small time window.
- Test with an authenticator emulator instead of a phone.

# 2 · Build: API contract

## Endpoints

| Method | Path                               | Purpose                                                                                                                         |
|--------|------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| `POST` | `/2fa/totp`                        | The fallback: `{email, password, code}`. A token with `signedInWith` `pwd otp mfa`.                                             |
| `POST` | `/webauthn/registration/options`   | Needs a token from the last 5 minutes. The options for `navigator.credentials.create()`.                                        |
| `POST` | `/webauthn/registration`           | `{label, credential}`: the browser's answer. `201`.                                                                             |
| `POST` | `/webauthn/authentication/options` | Open. The options for `navigator.credentials.get()`. (Not in the roadmap's list: a sign-in needs its challenge from somewhere.) |
| `POST` | `/webauthn/authentication`         | The browser's answer. A token with `signedInWith` `hwk user`.                                                                   |
| `GET`  | `/accounts/me`                     | Name and balance (in paise) of the signed-in customer.                                                                          |

## Status codes

| Status    | When                                                                                        |
|-----------|---------------------------------------------------------------------------------------------|
| 200 / 201 | Signed in, options given / passkey registered                                               |
| 400       | A body of the wrong shape; a registration answer that fails a check                         |
| 401       | Wrong email, password or code (one answer); a sign-in answer that fails any check; no token |
| 403       | Adding a passkey with a sign-in older than 5 minutes                                        |

## Captured examples

Captured with curl from the running app on 21 Oct 2026. curl has no authenticator, so the two passkey ceremonies themselves run in the tests, with webauthn4j's emulator; here are the code sign-in, both option documents, and what is refused. `Date`, connection and standard security headers are left out; the token and the code are shown by name.

### Case 1: password and the current code

**Why:** both factors in one request; the token records them.

Request

``` code
POST /2fa/totp HTTP/1.1
Content-Type: application/json

{
  "email": "zoya@example.com",
  "password": "zoya-demo-pass",
  "code": "<current code>"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 349

{
  "accessToken": "<access token>",
  "tokenType": "Bearer",
  "expiresIn": 600,
  "signedInWith": [
    "pwd",
    "otp",
    "mfa"
  ]
}
```

### Case 2: the same code again

**Why:** a code works once: `401`, the same answer as a wrong code.

Request

``` code
POST /2fa/totp HTTP/1.1
Content-Type: application/json

{
  "email": "zoya@example.com",
  "password": "zoya-demo-pass",
  "code": "<current code>"
}
```

Response

``` code
HTTP/1.1 401 
Content-Type: application/problem+json

{
  "detail": "Wrong email, password or code",
  "instance": "/2fa/totp",
  "status": 401,
  "title": "Unauthorized"
}
```

### Case 3: the account

**Why:** the token's customer; the balance is in paise.

Request

``` code
GET /accounts/me HTTP/1.1
Authorization: Bearer <access token>
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 78

{
  "name": "Zoya Khan",
  "balancePaise": 4250000,
  "signedInWith": [
    "pwd",
    "otp",
    "mfa"
  ]
}
```

### Case 4: options to add a passkey

**Why:** a fresh challenge, Tijori's domain, a random user id (not the email), a passkey that stays on the device, a fingerprint or face required.

Request

``` code
POST /webauthn/registration/options HTTP/1.1
Authorization: Bearer <access token>
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 445

{
  "challenge": "a8DFkXlE-bKVZfor_VhF4MFBUnwCSbAIBCJghTTtOoA",
  "rp": {
    "id": "tijori.example",
    "name": "Tijori"
  },
  "user": {
    "id": "CSzmQsYzRE7x2vLTFwU-MX6q8wBIQKFxryil8HbqPS8",
    "name": "zoya@example.com",
    "displayName": "Zoya Khan"
  },
  "pubKeyCredParams": [
    {
      "alg": -7,
      "type": "public-key"
    },
    {
      "alg": -257,
      "type": "public-key"
    }
  ],
  "timeout": 300000,
  "excludeCredentials": [],
  "authenticatorSelection": {
    "residentKey": "required",
    "userVerification": "required"
  },
  "attestation": "none"
}
```

### Case 5: options to sign in

**Why:** no user named: the passkey says whose it is.

Request

``` code
POST /webauthn/authentication/options HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 152

{
  "challenge": "L5kPdgqsjxnE7D-xhrr6E_2lMnzwBNrQLne1Oz2mktQ",
  "rpId": "tijori.example",
  "timeout": 300000,
  "allowCredentials": [],
  "userVerification": "required"
}
```

### Case 6: a made-up passkey answers case 5's challenge, from another page

**Why:** `401`, and the challenge is now used up (below).

Request

``` code
POST /webauthn/authentication HTTP/1.1
Content-Type: application/json

{
  "id": "AAAAAAAAAAAAAAAAAAAAAA",
  "rawId": "AAAAAAAAAAAAAAAAAAAAAA",
  "type": "public-key",
  "response": {
    "clientDataJSON": "<clientDataJSON naming tijori-login.example>",
    "authenticatorData": "AA",
    "signature": "AA",
    "userHandle": "AA"
  }
}
```

Response

``` code
HTTP/1.1 401 
Content-Type: application/problem+json

{
  "detail": "The passkey check failed. Try again.",
  "instance": "/webauthn/authentication",
  "status": 401,
  "title": "Unauthorized"
}
```

### Case 7: adding a passkey without signing in

**Why:** `401`.

Request

``` code
POST /webauthn/registration/options HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Bearer
Content-Type: application/problem+json
Content-Length: 149

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid access token: sign in again to get one.",
  "instance": "/webauthn/registration/options"
}
```

## What the database holds afterwards

From `psql` in `docs/capture.sh`.

``` code
    purpose     | for_a_customer | valid_for | used 
----------------+----------------+-----------+------
 registration   | t              | 00:05:00  | f
 authentication | f              | 00:05:00  | t
(2 rows)
```

``` code
      email       | user_handle_bytes | a_code_was_used | balance_paise 
------------------+-------------------+-----------------+---------------
 zoya@example.com |                32 | t               |       4250000
 dev@example.com  |                32 | f               |       1890050
(2 rows)
```

The sign-in challenge was used up by the made-up answer in case 6, so it can never be answered again. The registration challenge from case 4 is still open; it expires 5 minutes after it was made. Zoya's used code is recorded as a time step, not as the code.

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                           | What happens                                                        | Proved by                                                                                 |
|------------------------------------------------|---------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| Password and code                              | A token that opens the account                                      | `passwordAndCodeGiveATokenThatOpensTheAccount`                                            |
| Registration options                           | Tijori's domain, a random user id, passkey and fingerprint required | `registrationOptionsNameThisSiteAndAskForAPasskeyWithUserVerification`                    |
| Register, then sign in                         | No password needed                                                  | `aRegisteredPasskeySignsInWithoutAPassword`                                               |
| Wrong password, wrong code, unknown email      | The same `401`                                                      | `wrongPasswordWrongCodeOrUnknownEmailAreTheSame401`                                       |
| Bad bodies                                     | `400`                                                               | `badBodiesAre400`                                                                         |
| No token                                       | `401`                                                               | `noTokenIs401`                                                                            |
| A sign-in older than 5 minutes adds a passkey  | `403`                                                               | `addingAPasskeyNeedsASignInFromTheLastFiveMinutes`                                        |
| A registration on another customer's challenge | `400`, nothing stored                                               | `aChallengeIssuedToAnotherCustomerCannotAddAPasskeyHere`                                  |
| A passkey answer claiming another customer     | `401`                                                               | `aPasskeyCannotSayItBelongsToAnotherCustomer`                                             |
| A challenge after 5 minutes                    | `401`                                                               | `aChallengeExpiresAfterFiveMinutes`                                                       |
| A counter lower than the stored one            | `401`: it looks like a copied key                                   | `aCounterThatGoesBackwardsLooksLikeACloneAndIsRefused`                                    |
| A code twice; one step late; two steps late    | `401`; accepted; `401`                                              | `aCodeWorksOnceAndOnlyNearItsTime`                                                        |
| Ten sign-ins with one code at once             | Exactly one token                                                   | `tenParallelSignInsWithOneCodeGiveOneToken`                                               |
| Odd answers                                    | `400` or `401`, never an error                                      | `oddAnswersAre400Or401NeverAnError`                                                       |
| Rules written by plain SQL                     | Refused by named constraints                                        | `challengeRulesHoldWithoutJava`, `passkeyAndCustomerRulesHoldWithoutJava`                 |
| A save that fails; a check that fails          | Rolled back, retry works; the challenge is used up                  | `aSaveThatFailsRollsBackAndTheSameAnswerCanBeSentAgain`, `aFailedCheckUsesUpTheChallenge` |

## The trap

Plausible but wrong

Not checking the challenge, origin and relying-party id, so a phishing site can replay a sign-in.

The old code checked only that the signature matched the stored public key. Each test makes one answer it accepted:

- **Replayed.** A real sign-in, sent again a minute later: the signature is still valid. The API refuses it, because its challenge was used up. The test device keeps its counter at 0, as synced passkeys commonly do, so only the challenge stops this.
- **Answered for a phishing page.** `tijori-login.example` fetches a real challenge and gets the passkey to answer it on its own page: valid signature, wrong origin. Refused.
- **Made for another site.** A look-alike page asks for a passkey for its own domain and hands it to Tijori. The old code stored any key it could parse. Refused.
- **The control.** A fresh challenge on Tijori's page signs in.

While building, each check was undone once: the sign-in challenge taken from the request turned 3 tests red; any origin 1; no userHandle comparison 1; no owner check on the registration challenge 1; registration without its transaction 1, or rolling back on every failure 1; no recent sign-in check 1; a reusable code 2; no one-step window 1; the counter not stored 1. Not requiring user verification turned nothing red: the emulator always reports it.

``` code
package com.tijori.passkeys;

import com.webauthn4j.WebAuthnManager;
import com.webauthn4j.converter.AttestedCredentialDataConverter;
import com.webauthn4j.converter.util.ObjectConverter;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

import java.io.ByteArrayOutputStream;
import java.security.MessageDigest;
import java.security.Signature;
import java.util.Base64;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old passkey code checked only the signature with the stored public key: not which challenge was
 * signed, not which page asked, not which site the passkey was made for. Each test builds one answer the old code
 * accepted, then sends it to the real API.
 */
class UncheckedCeremonyTrapTest extends ApiTest {

    static final Base64.Decoder UNB64 = Base64.getUrlDecoder();

    /** The old sign-in check, as it was: is this a valid signature by the stored key? */
    boolean oldSignatureOnlyCheck(JsonNode assertion) throws Exception {
        byte[] stored = jdbc.sql("SELECT attested_credential_data FROM passkeys WHERE credential_id = ?")
                .param(UNB64.decode(assertion.path("rawId").asString())).query(byte[].class).single();
        var key = new AttestedCredentialDataConverter(new ObjectConverter()).convert(stored).getCOSEKey().getPublicKey();
        JsonNode r = assertion.path("response");
        ByteArrayOutputStream signed = new ByteArrayOutputStream();
        signed.write(UNB64.decode(r.path("authenticatorData").asString()));
        signed.write(MessageDigest.getInstance("SHA-256").digest(UNB64.decode(r.path("clientDataJSON").asString())));
        Signature verifier = Signature.getInstance("SHA256withECDSA");
        verifier.initVerify(key);
        verifier.update(signed.toByteArray());
        return verifier.verify(UNB64.decode(r.path("signature").asString()));
    }

    @Test
    void aSignInCapturedOnceAndSentAgainIsRefused() throws Exception {
        Device phone = passkeyFor("zoya");
        ObjectNode signIn = phone.get(authenticationOptions());
        authenticate(signIn).andExpect(status().isOk());
        // Captured from a log or a proxy: the very same answer, a minute later. A synced passkey's counter stays 0,
        // so only the used-up challenge stops it.
        later(java.time.Duration.ofMinutes(1));
        assertThat(oldSignatureOnlyCheck(signIn)).isTrue();             // the old code: signed in again
        authenticate(signIn).andExpect(status().isUnauthorized());      // its challenge was used up
    }

    @Test
    void aSignInAnsweredForAPhishingPageIsRefused() throws Exception {
        Device phone = passkeyFor("zoya");
        // tijori-login.example fetches a real challenge from Tijori and gets the passkey to answer it on its own page.
        ObjectNode relayed = phone.at("https://tijori-login.example").get(authenticationOptions());
        assertThat(oldSignatureOnlyCheck(relayed)).isTrue();
        authenticate(relayed).andExpect(status().isUnauthorized());     // clientDataJSON names the page that asked
    }

    @Test
    void aPasskeyMadeForAnotherSiteIsNotRegistered() throws Exception {
        String token = codeToken("zoya");
        // A look-alike page asks for a passkey for its own relying party, then hands the result to Tijori.
        ObjectNode forOtherSite = new Device().create(registrationOptions(token), "tijori-login.example");
        assertThat(WebAuthnManager.createNonStrictWebAuthnManager().parseRegistrationResponseJSON(forOtherSite.toString())).isNotNull();   // the old code stored any parsable key
        register(token, "Zoya's phone", forOtherSite).andExpect(status().isBadRequest());
        assertThat(jdbc.sql("SELECT count(*) FROM passkeys").query(Long.class).single()).isZero();
    }

    @Test
    void theRightAnswerSignsIn() throws Exception {
        // The control: same passkey, Tijori's own page, a fresh challenge.
        Device phone = passkeyFor("zoya");
        authenticate(phone.get(authenticationOptions())).andExpect(status().isOk());
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
./mvnw test                 # all 22 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Make the current code from the demo secret and sign in with it, twice:

``` code
CODE=$(python3 -c 'import hmac,hashlib,struct,time; h=hmac.new(b"12345678901234567890",struct.pack(">Q",int(time.time())//30),hashlib.sha1).digest(); o=h[-1]&15; print("%06d"%((int.from_bytes(h[o:o+4],"big")&0x7fffffff)%1000000))')
for i in 1 2; do curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8080/2fa/totp -H 'Content-Type: application/json' \
  -d "{\"email\": \"dev@example.com\", \"password\": \"dev-demo-pass\", \"code\": \"$CODE\"}"; done
```

The first prints 200, the second 401. Any authenticator app set up with the base32 secret `GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ` shows the same codes. A real passkey needs a browser on HTTPS at the configured origin; to see the ceremonies, run `./mvnw test -Dtest=PasskeyContractTest`.

## Troubleshooting

| You see                                                           | Cause                                                                                                  | Fix                                                                                                |
|-------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| Every passkey sign-in is `401`, the log says `BadOriginException` | The page's origin differs from `tijori.webauthn.origin` (port, http against https, another subdomain). | Configure the exact origin; list every real one, never all.                                        |
| `BadRpIdException`                                                | The passkey was made for another RP id.                                                                | The RP id is the registrable domain the passkeys were created for; changing it later orphans them. |
| Codes are always wrong                                            | The server clock is off by more than 30 seconds.                                                       | Keep server clocks in sync (NTP).                                                                  |
| `MaliciousCounterValueException`                                  | The counter went backwards: a copied key, or a restored backup of the table.                           | Treat it as a warning about that passkey; ask the customer.                                        |

## Project layout

``` tree
stations/076-passkey-sign-in-with-webauthn/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tijori/passkeys/
│   ├── SecurityConfig.java   ├── SignInController.java   ├── Passkeys.java
│   ├── CodeSignIn.java   ├── Totp.java   ├── TokenService.java   ├── JwtConfig.java
│   ├── AccountController.java   ├── ProblemResponses.java   └── PasskeysApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__customers_passkeys_challenges.sql, V2__demo_customers.sql
├── src/test/java/com/tijori/passkeys/   Device.java (the emulated phone) and the tests
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/tijori/passkeys/SecurityConfig.java`

Does  
Who may call what.

Why  
The sign-in ceremonies and the code sign-in are open (they are the proof); adding a passkey and the account need a token; everything else refused.

Without it  
A passkey added by someone who is not signed in, or a new endpoint open by default.

#### `src/main/java/com/tijori/passkeys/SignInController.java`

Does  
The five sign-in endpoints.

Why  
Password and code together, never apart; adding a passkey needs a sign-in from the last 5 minutes; one answer for every failed ceremony.

Without it  
A stolen token planting the attacker's own passkey, or errors that tell which check failed.

#### `src/main/java/com/tijori/passkeys/Passkeys.java`

Does  
Both WebAuthn ceremonies.

Why  
The challenge is ours and used up in one conditional `UPDATE`; then webauthn4j checks it with our origin and our RP id, user verification, the signature and the counter; the server compares `userHandle` itself.

Without it  
Replays, answers made for other pages or other sites, and one customer's passkey speaking for another.

- The signature covers the authenticator data and a hash of clientDataJSON, not `userHandle`: a changed `userHandle` keeps the signature valid. Found while building.
- Synced passkeys commonly report a counter of 0, so the counter cannot be relied on to stop replays: the challenge does. Found while building, when the replay test first stayed green.
- Both ceremonies are transactions with `noRollbackFor = CeremonyFailed`: a failed check still uses up its challenge, a failed save does not.

#### `src/main/java/com/tijori/passkeys/CodeSignIn.java`

Does  
The fallback: password and an authenticator-app code.

Why  
RFC 6238 codes for the current and the previous 30 seconds, compared in constant time, each accepted once (`totp_last_step` moves forward in one conditional UPDATE).

Without it  
A code read over a shoulder being used again, or two requests with one code both getting in.

No attempt limit yet: a six-digit code has a million values. Challenge 2 adds one.

#### `src/main/java/com/tijori/passkeys/Totp.java`

The code itself: HMAC-SHA1 over the step number, dynamic truncation, six digits.

#### `src/main/java/com/tijori/passkeys/TokenService.java`

10-minute tokens; `amr` (RFC 8176 values) records how the customer signed in.

#### `src/main/java/com/tijori/passkeys/JwtConfig.java`

The token checks, as in station 073.

#### `src/main/java/com/tijori/passkeys/AccountController.java`

The account from the token's subject.

#### `src/main/java/com/tijori/passkeys/ProblemResponses.java`

401 and 403 in the same problem JSON as every other error.

#### `src/main/resources/db/migration/V1__customers_passkeys_challenges.sql`

Does  
Customers, passkeys and challenges, with their rules.

Why  
32-byte challenges for 5 minutes at most; a registration challenge always belongs to a customer; a counter within 32 bits; a random 32-byte user id.

Without it  
A script storing eternal challenges, or a passkey whose owner could be guessed from its user id.

#### `src/main/resources/db/migration/V2__demo_customers.sql`

Two demo customers, bcrypt hashes made by pgcrypto, and RFC 6238's public test secret.

#### `src/main/resources/application.yaml`

The RP id, the one allowed origin, lifetimes, and a demo signing key.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/tijori/passkeys/PasskeysApplication.java`

Entry point, and the `Clock` every time check uses.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                      | Result |
|---------------|-------------------------------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `PasskeyContractTest` (5)       | pass   |
| Every station | Reproduce the failure before the fix                              | `UncheckedCeremonyTrapTest` (4) | pass   |
| Database      | Rollback and constraint tests against a real database             | `PasskeyDatabaseTest` (4)       | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `PasskeySecurityTest` (9)       | pass   |

"Not found" here is the unknown email and the unknown passkey, both answered like a wrong one on purpose. "Another user's data": a passkey claiming another customer, and a registration on another customer's challenge. `Device` wraps webauthn4j's emulator: a `NoneAttestationAuthenticator` behind a `ClientPlatform` at an origin, turning the server's options into the JSON a browser sends.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, webauthn4j 0.31.9, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 9, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.passkeys.PasskeySecurityTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.passkeys.PasskeyDatabaseTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.passkeys.UncheckedCeremonyTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.passkeys.PasskeyContractTest
[INFO] Tests run: 22, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/passkeys/UncheckedCeremonyTrapTest.java`

Written first: three answers the signature-only check accepted, each refused by the API, and the control.

#### `src/test/java/com/tijori/passkeys/PasskeySecurityTest.java`

401, 403, other customers, expiry, a copied key, codes once and near their time, ten parallel sign-ins, odd answers.

#### `src/test/java/com/tijori/passkeys/PasskeyDatabaseTest.java`

Every named constraint with plain SQL; a save that fails rolls back, a check that fails uses the challenge up.

#### `src/test/java/com/tijori/passkeys/PasskeyContractTest.java`

Code sign-in, both ceremonies, wrong answers, bad bodies.

#### `src/test/java/com/tijori/passkeys/Device.java`

The emulated phone: authenticator and browser, at an origin.

#### `src/test/java/com/tijori/passkeys/ApiTest.java`

Shared setup: the test clock, a test key, a clean slate before each test, ceremony helpers.

#### `src/test/java/com/tijori/passkeys/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/passkeys/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ManagePasskeysChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 22 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 26 tests pass (22 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## List and remove passkeys

`GET /webauthn/passkeys` lists the customer's own passkeys (id, label); `DELETE /webauthn/passkeys/{id}` removes one (`204`), after which it cannot sign in. Another customer's passkey is `404` and stays.

**Done when:** both tests in `ManagePasskeysChallengeTest` pass.

Hints

- Put the customer in the `DELETE`'s `WHERE`: another customer's id then finds no row.
- The filter chain refuses new paths until they have a rule.

#### `challenge/ManagePasskeysChallengeTest.java`

``` code
package com.tijori.passkeys;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /webauthn/passkeys lists the customer's own passkeys (id, label); DELETE /webauthn/passkeys/{id}
 * removes one (204), after which it cannot sign in. Another customer's passkey is 404 and stays.
 */
class ManagePasskeysChallengeTest extends ApiTest {

    @Test
    void aCustomerListsAndRemovesTheirOwnPasskey() throws Exception {
        Device phone = passkeyFor("zoya");
        String token = codeToken("zoya");
        String id = body(mvc.perform(get("/webauthn/passkeys").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk()).andExpect(jsonPath("$[*].label", contains("zoya's phone")))).get(0).get("id").asString();
        mvc.perform(delete("/webauthn/passkeys/{id}", id).header("Authorization", "Bearer " + token)).andExpect(status().isNoContent());
        authenticate(phone.get(authenticationOptions())).andExpect(status().isUnauthorized());
    }

    @Test
    void anotherCustomersPasskeyIs404AndStays() throws Exception {
        Device zoyasPhone = passkeyFor("zoya");
        String zoyasId = body(mvc.perform(get("/webauthn/passkeys").header("Authorization", "Bearer " + codeToken("zoya")))).get(0).get("id").asString();
        mvc.perform(delete("/webauthn/passkeys/{id}", zoyasId).header("Authorization", "Bearer " + codeToken("dev"))).andExpect(status().isNotFound());
        authenticate(zoyasPhone.get(authenticationOptions())).andExpect(status().isOk());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 40 minutes

## Lock code sign-in after five wrong codes

After 5 wrong codes in a row (with the right password), code sign-in is locked for 15 minutes; even the right code then gets the same `401`. A good sign-in resets the count.

**Done when:** both tests in `CodeLockoutChallengeTest` pass.

Hints

- Two columns in a V3 migration, with a CHECK on the count.
- Lock the customer row (`SELECT ... FOR UPDATE`) so parallel guesses are counted one by one.
- A code that was already used is a replay, not a guess: do not count it, or ten parallel requests lock the account.

#### `challenge/CodeLockoutChallengeTest.java`

``` code
package com.tijori.passkeys;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a six-digit code has a million values. After 5 wrong codes in a row (with the right password), code
 * sign-in is locked for 15 minutes: even the right code is refused with the same 401. A good sign-in resets the count.
 */
class CodeLockoutChallengeTest extends ApiTest {

    @org.junit.jupiter.api.BeforeEach
    void noFailedCodes() {
        jdbc.sql("UPDATE customers SET failed_codes = 0, codes_locked_until = NULL").update();   // other tests may have tried a wrong code
    }

    static String wrong(String right) {
        return right.equals("000000") ? "111111" : "000000";
    }

    @Test
    void fiveWrongCodesLockCodeSignInForFifteenMinutes() throws Exception {
        for (int i = 0; i < 5; i++) {
            codeSignIn("dev@example.com", "dev-demo-pass", wrong(currentCode())).andExpect(status().isUnauthorized());
        }
        codeSignIn("dev@example.com", "dev-demo-pass", currentCode()).andExpect(status().isUnauthorized());
        later(Duration.ofMinutes(15).plusSeconds(1));
        codeSignIn("dev@example.com", "dev-demo-pass", currentCode()).andExpect(status().isOk());
    }

    @Test
    void aGoodSignInResetsTheCount() throws Exception {
        for (int i = 0; i < 4; i++) {
            codeSignIn("dev@example.com", "dev-demo-pass", wrong(currentCode())).andExpect(status().isUnauthorized());
        }
        codeSignIn("dev@example.com", "dev-demo-pass", currentCode()).andExpect(status().isOk());
        later(Duration.ofSeconds(30));
        codeSignIn("dev@example.com", "dev-demo-pass", wrong(currentCode())).andExpect(status().isUnauthorized());
        codeSignIn("dev@example.com", "dev-demo-pass", currentCode()).andExpect(status().isOk());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Lost phone, and the apps

A customer loses the only phone with their passkey and their code app. Design recovery without SMS: what identity checks, what waiting period, and what the customer is told. Then: Tijori's Android app sends `android:apk-key-hash:...` as its origin. How do you accept it without accepting every origin?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: answers a signature-only check accepted, made with an emulated phone.
2.  Store challenges in the database, single-use, with their purpose and owner.
3.  Let webauthn4j check the answers against our challenge, our origin and our RP id.
4.  Add the password-plus-code fallback, with single-use codes.

## Design alternatives and trade-offs

| Approach                                                  | What it costs                                                  | Verdict                              |
|-----------------------------------------------------------|----------------------------------------------------------------|--------------------------------------|
| Own endpoints on webauthn4j, challenges in PostgreSQL     | More code than a built-in; every check visible.                | Chosen                               |
| Check only the signature                                  | Replays and answers for other pages pass.                      | The trap                             |
| Spring Security's `webAuthn()` DSL                        | Little code; its own endpoint names and session-based options. | Good for a web app with sessions     |
| SMS codes as the fallback                                 | SIM swaps; the original incident.                              | Not here                             |
| Ask for attestation and trust only certain authenticators | Metadata service, privacy prompts; for regulated keys.         | When the authenticator model matters |

## Database design

| Object                                               | What                                | Why                                                              |
|------------------------------------------------------|-------------------------------------|------------------------------------------------------------------|
| `webauthn_challenges_length`, `_expiry`              | CHECKs: 32 bytes, at most 5 minutes | No guessable or eternal challenges from any writer.              |
| `webauthn_challenges_registration_has_customer`      | CHECK                               | A registration challenge always belongs to one customer.         |
| `passkeys_sign_count_range`, `_credential_id_length` | CHECKs                              | What WebAuthn allows: a 32-bit counter, ids of 16 to 1023 bytes. |
| `customers_user_handle_length`, `_unique`            | CHECK and UNIQUE                    | A random 32-byte id per customer, never the email.               |
| `customers_totp_secret_length`                       | CHECK: at least 20 bytes            | RFC 4226's minimum of 128 bits, recommended 160.                 |

**Transaction boundary:** one ceremony is one transaction. A failed check commits (the challenge stays used); a failed save rolls back (the same answer can be sent again).

``` code
CREATE TABLE customers (
    id             bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT customers_pk PRIMARY KEY,
    email          text NOT NULL,
    name           text NOT NULL,
    -- WebAuthn's user.id: random bytes, never the email, so a passkey reveals nothing about who it belongs to.
    user_handle    bytea NOT NULL,
    password_hash  text NOT NULL,
    totp_secret    bytea NOT NULL,
    -- The last 30-second step whose code was accepted: a code works once.
    totp_last_step bigint,
    balance_paise  bigint NOT NULL,
    CONSTRAINT customers_email_lower CHECK (email = lower(email)),
    CONSTRAINT customers_email_unique UNIQUE (email),
    CONSTRAINT customers_user_handle_unique UNIQUE (user_handle),
    CONSTRAINT customers_user_handle_length CHECK (octet_length(user_handle) = 32),
    CONSTRAINT customers_password_hash_shape CHECK (password_hash ~ '^\{bcrypt\}\$2[aby]\$(1[0-9]|2[0-9]|3[01])\$[./A-Za-z0-9]{53}$'),
    CONSTRAINT customers_totp_secret_length CHECK (octet_length(totp_secret) >= 20),
    CONSTRAINT customers_balance_nonnegative CHECK (balance_paise >= 0)
);

CREATE TABLE passkeys (
    credential_id            bytea CONSTRAINT passkeys_pk PRIMARY KEY,
    customer_id              bigint NOT NULL CONSTRAINT passkeys_customer_fk REFERENCES customers ON DELETE CASCADE,
    -- The authenticator's AAGUID, the credential id and the COSE public key, as the authenticator sent them.
    attested_credential_data bytea NOT NULL,
    sign_count               bigint NOT NULL,
    label                    text NOT NULL,
    created_at               timestamptz NOT NULL,
    last_used_at             timestamptz,
    CONSTRAINT passkeys_credential_id_length CHECK (octet_length(credential_id) BETWEEN 16 AND 1023),
    CONSTRAINT passkeys_sign_count_range CHECK (sign_count BETWEEN 0 AND 4294967295),
    CONSTRAINT passkeys_label_length CHECK (char_length(label) BETWEEN 1 AND 60)
);

-- Every ceremony starts with a random challenge from the server; each is good once, for 5 minutes.
CREATE TABLE webauthn_challenges (
    challenge   bytea CONSTRAINT webauthn_challenges_pk PRIMARY KEY,
    purpose     text NOT NULL,
    customer_id bigint CONSTRAINT webauthn_challenges_customer_fk REFERENCES customers ON DELETE CASCADE,
    created_at  timestamptz NOT NULL,
    expires_at  timestamptz NOT NULL,
    used_at     timestamptz,
    CONSTRAINT webauthn_challenges_length CHECK (octet_length(challenge) = 32),
    CONSTRAINT webauthn_challenges_purpose CHECK (purpose IN ('registration', 'authentication')),
    CONSTRAINT webauthn_challenges_registration_has_customer CHECK (purpose <> 'registration' OR customer_id IS NOT NULL),
    CONSTRAINT webauthn_challenges_expiry CHECK (expires_at > created_at AND expires_at <= created_at + interval '5 minutes'),
    CONSTRAINT webauthn_challenges_used_in_time CHECK (used_at IS NULL OR used_at >= created_at)
);
```

# 3 · Go deeper: Production

Origins  
List every real origin (web, Android's `android:apk-key-hash:`, iOS uses the web origin through associated domains). Never accept any origin.

Old challenges  
Delete used and expired challenges in a scheduled job.

TOTP secrets  
Store them encrypted (they are not hashes: the server needs them), and show the QR code only once.

Logs  
Log which check failed; never log codes, tokens or full credential JSON.

Standards  
Web Authentication Level 2 is a W3C Recommendation (2021); Level 3, which adds the JSON forms used here, was still being finished at W3C when this was written: check its status before citing it; CTAP 2 is a FIDO Alliance specification; TOTP is RFC 6238 and HOTP RFC 4226 (both Informational); `amr` values are RFC 8176 (Proposed Standard).

# 3 · Go deeper: Interview

## Interview takeaways

Why are passkeys phishing-resistant?

The browser gives a passkey only to pages of the domain it was made for, and the signed data names the page's origin. A look-alike domain cannot use it, and the server refuses answers for other origins.

What does the server check on a passkey sign-in?

That the challenge is its own, unused and in time; the origin and RP id hash; the user-presence and user-verification flags; the signature with the stored public key; the counter; and that userHandle matches the passkey's owner.

Why store challenges server-side?

So each is used once. A random challenge that the server does not remember can be answered again by anyone who recorded the answer.

What is the signature counter for?

Cloned-key detection: a counter that does not increase suggests two copies of a key. Synced passkeys usually report 0, so it is a signal, not a replay defence.

Why TOTP and not SMS as the fallback?

SMS can be redirected by a SIM swap or intercepted. TOTP lives in an app on the device. It can still be phished, which is why passkeys are the main way in.

## Self-check rubric

| Area        | Meets the bar                                | Above the bar                                                                    |
|-------------|----------------------------------------------|----------------------------------------------------------------------------------|
| Correctness | All 22 tests pass.                           | You ran the flawed version and explained each failure.                           |
| Ceremonies  | Challenge, origin, RP id, signature checked. | userHandle compared; counter kept; you know why 0 is common.                     |
| Fallback    | Password and code together.                  | Codes single-use under parallel requests.                                        |
| Data        | Challenges single-use.                       | Each rule a named constraint; failed checks and failed saves behave differently. |

# 3 · Go deeper: Review

## The pull request

A teammate unblocks the Android app and staging ("they send other origins"), drops the challenge table lookup at sign-in ("challenges are random 32 bytes and signed anyway"), and removes the fresh sign-in needed to add a passkey ("customers complained"). Read the two files and list every problem before opening the findings.

#### `review/Passkeys.java`

``` code
package com.tijori.passkeys;

import com.webauthn4j.WebAuthnManager;
import com.webauthn4j.converter.AttestedCredentialDataConverter;
import com.webauthn4j.converter.util.ObjectConverter;
import com.webauthn4j.credential.CredentialRecordImpl;
import com.webauthn4j.data.AuthenticationData;
import com.webauthn4j.data.AuthenticationParameters;
import com.webauthn4j.data.PublicKeyCredentialParameters;
import com.webauthn4j.data.PublicKeyCredentialType;
import com.webauthn4j.data.RegistrationData;
import com.webauthn4j.data.RegistrationParameters;
import com.webauthn4j.data.attestation.authenticator.AttestedCredentialData;
import com.webauthn4j.data.attestation.statement.COSEAlgorithmIdentifier;
import com.webauthn4j.data.attestation.statement.NoneAttestationStatement;
import com.webauthn4j.data.client.Origin;
import com.webauthn4j.data.client.challenge.DefaultChallenge;
import com.webauthn4j.data.extension.authenticator.AuthenticationExtensionsAuthenticatorOutputs;
import com.webauthn4j.data.extension.client.AuthenticationExtensionsClientOutputs;
import com.webauthn4j.server.ServerProperty;
import com.webauthn4j.verifier.exception.VerificationException;
import com.webauthn4j.converter.exception.DataConversionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * The two WebAuthn ceremonies. Each starts with a challenge from this server and ends with webauthn4j checking the
 * browser's answer against three values that come from here, never from the request: the challenge we issued, our
 * origin, and our relying-party id. Then the signature, user verification and the signature counter.
 */
@Service
class Passkeys {

    private static final Logger log = LoggerFactory.getLogger(Passkeys.class);
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Base64.Encoder B64 = Base64.getUrlEncoder().withoutPadding();
    private static final Base64.Decoder UNB64 = Base64.getUrlDecoder();
    /** ES256 and RS256: what platform authenticators and security keys offer. */
    static final List<PublicKeyCredentialParameters> ALGORITHMS = List.of(
            new PublicKeyCredentialParameters(PublicKeyCredentialType.PUBLIC_KEY, COSEAlgorithmIdentifier.ES256),
            new PublicKeyCredentialParameters(PublicKeyCredentialType.PUBLIC_KEY, COSEAlgorithmIdentifier.RS256));

    /** The browser's answer failed a check. Which one is logged, not told. */
    static final class CeremonyFailed extends RuntimeException {
        CeremonyFailed(String reason) {
            super(reason);
        }
    }

    private final JdbcClient jdbc;
    private final Clock clock;
    private final String rpId;
    private final String rpName;
    private final Origin origin;
    private final Duration challengeLifetime;
    private final ObjectConverter converter = new ObjectConverter();
    private final WebAuthnManager webAuthn = WebAuthnManager.createNonStrictWebAuthnManager(converter);
    private final AttestedCredentialDataConverter credentialData = new AttestedCredentialDataConverter(converter);

    Passkeys(JdbcClient jdbc, Clock clock, @Value("${tijori.webauthn.rp-id}") String rpId, @Value("${tijori.webauthn.rp-name}") String rpName,
             @Value("${tijori.webauthn.origin}") String origin, @Value("${tijori.webauthn.challenge-lifetime}") Duration challengeLifetime) {
        this.jdbc = jdbc;
        this.clock = clock;
        this.rpId = rpId;
        this.rpName = rpName;
        this.origin = new Origin(origin);
        this.challengeLifetime = challengeLifetime;
    }

    private record Customer(String email, String name, byte[] userHandle) {
    }

    /** What the browser passes to navigator.credentials.create(), as JSON. */
    Map<String, Object> registrationOptions(long customerId) {
        Customer c = jdbc.sql("SELECT email, name, user_handle FROM customers WHERE id = ?").param(customerId).query(Customer.class).single();
        List<Map<String, String>> existing = jdbc.sql("SELECT credential_id FROM passkeys WHERE customer_id = ?").param(customerId)
                .query(byte[].class).list().stream().map(id -> Map.of("type", "public-key", "id", B64.encodeToString(id))).toList();
        Map<String, Object> options = new LinkedHashMap<>();
        options.put("challenge", newChallenge("registration", customerId));
        options.put("rp", Map.of("id", rpId, "name", rpName));
        options.put("user", Map.of("id", B64.encodeToString(c.userHandle()), "name", c.email(), "displayName", c.name()));
        options.put("pubKeyCredParams", ALGORITHMS.stream().map(p -> Map.of("type", "public-key", "alg", p.getAlg().getValue())).toList());
        options.put("timeout", challengeLifetime.toMillis());
        options.put("excludeCredentials", existing);   // the same authenticator is not registered twice
        options.put("authenticatorSelection", Map.of("residentKey", "required", "userVerification", "required"));
        options.put("attestation", "none");
        return options;
    }

    /**
     * Checks the new passkey and stores its public key. Returns its credential id. One transaction: a failed check
     * still uses up the challenge (no second try with it), but a failed save rolls back, so the same answer can be sent again.
     */
    @Transactional(noRollbackFor = CeremonyFailed.class)
    String register(long customerId, String label, JsonNode credential) {
        byte[] challenge = useChallenge(credential, "registration")
                .filter(owner -> owner == customerId)   // a challenge issued to someone else proves nothing for this customer
                .map(owner -> clientChallenge(credential)).orElseThrow(() -> new CeremonyFailed("unknown, used, expired or someone else's challenge"));
        RegistrationData data;
        try {
            data = webAuthn.verifyRegistrationResponseJSON(credential.toString(),
                    new RegistrationParameters(server(challenge), ALGORITHMS, true, true));
        } catch (VerificationException | DataConversionException e) {
            log.info("Passkey registration refused: {}", e.getClass().getSimpleName());
            throw new CeremonyFailed(e.getClass().getSimpleName());
        }
        AttestedCredentialData acd = data.getAttestationObject().getAuthenticatorData().getAttestedCredentialData();
        jdbc.sql("INSERT INTO passkeys (credential_id, customer_id, attested_credential_data, sign_count, label, created_at) VALUES (?, ?, ?, ?, ?, ?)")
                .params(acd.getCredentialId(), customerId, credentialData.convert(acd), data.getAttestationObject().getAuthenticatorData().getSignCount(),
                        label.strip(), now()).update();
        return B64.encodeToString(acd.getCredentialId());
    }

    /** What the browser passes to navigator.credentials.get(): no user named, the passkey says who it is. */
    Map<String, Object> authenticationOptions() {
        Map<String, Object> options = new LinkedHashMap<>();
        options.put("challenge", newChallenge("authentication", null));
        options.put("rpId", rpId);
        options.put("timeout", challengeLifetime.toMillis());
        options.put("allowCredentials", List.of());
        options.put("userVerification", "required");
        return options;
    }

    private record Stored(long customerId, byte[] userHandle, byte[] attestedCredentialData, long signCount) {
    }

    /** The customer whose passkey this is, after every check. One transaction, as for registration. */
    @Transactional(noRollbackFor = CeremonyFailed.class)
    long authenticate(JsonNode credential) {
        byte[] challenge = clientChallenge(credential);   // random 32 bytes, and the signature covers it: no table lookup needed
        byte[] credentialId = UNB64.decode(text(credential, "rawId"));
        Stored stored = jdbc.sql("""
                        SELECT p.customer_id, c.user_handle, p.attested_credential_data, p.sign_count
                        FROM passkeys p JOIN customers c ON c.id = p.customer_id WHERE p.credential_id = ?""")
                .param(credentialId).query(Stored.class).optional().orElseThrow(() -> new CeremonyFailed("unknown passkey"));
        // The passkey must also say it belongs to that customer (WebAuthn's userHandle check).
        if (!Arrays.equals(UNB64.decode(text(credential.path("response"), "userHandle")), stored.userHandle())) {
            throw new CeremonyFailed("userHandle does not match the passkey's customer");
        }
        CredentialRecordImpl record = new CredentialRecordImpl(new NoneAttestationStatement(), null, null, null, stored.signCount(),
                credentialData.convert(stored.attestedCredentialData()), new AuthenticationExtensionsAuthenticatorOutputs<>(), null,
                new AuthenticationExtensionsClientOutputs<>(), null);
        AuthenticationData data;
        try {
            data = webAuthn.verifyAuthenticationResponseJSON(credential.toString(),
                    new AuthenticationParameters(server(challenge), record, null, true, true));
        } catch (VerificationException | DataConversionException e) {
            log.info("Passkey sign-in refused: {}", e.getClass().getSimpleName());
            throw new CeremonyFailed(e.getClass().getSimpleName());
        }
        // A counter that goes backwards can mean a cloned authenticator; webauthn4j refuses it above. Store the new one.
        jdbc.sql("UPDATE passkeys SET sign_count = ?, last_used_at = ? WHERE credential_id = ?")
                .params(data.getAuthenticatorData().getSignCount(), now(), credentialId).update();
        return stored.customerId();
    }

    /** Any origin: the Android app sends android:apk-key-hash:..., and staging runs on its own domain. */
    private ServerProperty server(byte[] challenge) {
        return ServerProperty.builder().originPredicate(o -> true).rpId(rpId).challenge(new DefaultChallenge(challenge)).build();
    }

    private String newChallenge(String purpose, Long customerId) {
        byte[] challenge = new byte[32];
        RANDOM.nextBytes(challenge);
        OffsetDateTime created = now();   // one clock read: two would break the 5-minute CHECK
        jdbc.sql("INSERT INTO webauthn_challenges (challenge, purpose, customer_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?)")
                .params(challenge, purpose, customerId, created, created.plus(challengeLifetime)).update();
        return B64.encodeToString(challenge);
    }

    /**
     * Marks the challenge in the browser's clientDataJSON as used, if this server issued it for this purpose and it
     * is unused and in time: one conditional UPDATE, so a challenge works for exactly one answer. Returns its owner
     * (0 for sign-in challenges, which have none).
     */
    private Optional<Long> useChallenge(JsonNode credential, String purpose) {
        byte[] challenge;
        try {
            challenge = clientChallenge(credential);
        } catch (RuntimeException notOurShape) {
            return Optional.empty();
        }
        OffsetDateTime now = now();
        return jdbc.sql("UPDATE webauthn_challenges SET used_at = ? WHERE challenge = ? AND purpose = ? AND used_at IS NULL AND expires_at > ? RETURNING coalesce(customer_id, 0)")
                .params(now, challenge, purpose, now).query(Long.class).optional();
    }

    private static byte[] clientChallenge(JsonNode credential) {
        JsonNode clientData = JSON.readTree(UNB64.decode(text(credential.path("response"), "clientDataJSON")));
        return UNB64.decode(text(clientData, "challenge"));
    }

    private static String text(JsonNode node, String field) {
        JsonNode value = node.path(field);
        if (!value.isString()) {
            throw new CeremonyFailed("missing " + field);
        }
        return value.asString();
    }

    private OffsetDateTime now() {
        return OffsetDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
    }
}
```

#### `review/SignInController.java`

``` code
package com.tijori.passkeys;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;

import java.net.URI;
import java.time.Clock;
import java.time.Duration;
import java.util.List;
import java.util.Map;

@RestController
class SignInController {

    record CodeLogin(@NotBlank @Email @Size(max = 254) String email, @NotNull @Size(min = 1, max = 64) String password,
                     @NotNull @Pattern(regexp = "\\d{6}") String code) {
    }

    record NewPasskey(@NotBlank @Size(max = 60) String label, @NotNull JsonNode credential) {
    }

    /** Demo rule: adding a passkey needs a sign-in from the last 5 minutes, so a stolen token cannot plant one. */
    static final Duration RECENT_SIGN_IN = Duration.ofMinutes(5);

    private final CodeSignIn codes;
    private final Passkeys passkeys;
    private final TokenService tokens;
    private final Clock clock;

    SignInController(CodeSignIn codes, Passkeys passkeys, TokenService tokens, Clock clock) {
        this.codes = codes;
        this.passkeys = passkeys;
        this.tokens = tokens;
        this.clock = clock;
    }

    @PostMapping("/2fa/totp")
    TokenService.AccessToken codeSignIn(@Valid @RequestBody CodeLogin body) {
        long customer = codes.signIn(body.email(), body.password(), body.code())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Wrong email, password or code"));
        return tokens.issue(customer, List.of("pwd", "otp", "mfa"));
    }

    @PostMapping("/webauthn/registration/options")
    Map<String, Object> registrationOptions(@AuthenticationPrincipal Jwt jwt) {
        return passkeys.registrationOptions(recentlySignedIn(jwt));
    }

    @PostMapping("/webauthn/registration")
    ResponseEntity<Map<String, String>> register(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody NewPasskey body) {
        String id = passkeys.register(recentlySignedIn(jwt), body.label(), body.credential());
        return ResponseEntity.created(URI.create("/webauthn/passkeys/" + id)).body(Map.of("id", id, "label", body.label().strip()));
    }

    @PostMapping("/webauthn/authentication/options")
    Map<String, Object> authenticationOptions() {
        return passkeys.authenticationOptions();
    }

    @PostMapping("/webauthn/authentication")
    TokenService.AccessToken authenticate(@RequestBody JsonNode credential) {
        return tokens.issue(passkeys.authenticate(credential), List.of("hwk", "user"));
    }

    /** One answer for every failed ceremony; the reason goes to the log. Registration is 400: the caller is known. */
    @ExceptionHandler(Passkeys.CeremonyFailed.class)
    ResponseEntity<ProblemDetail> ceremonyFailed(Passkeys.CeremonyFailed e, HttpServletRequest request) {
        HttpStatus status = request.getRequestURI().startsWith("/webauthn/registration") ? HttpStatus.BAD_REQUEST : HttpStatus.UNAUTHORIZED;
        return ResponseEntity.status(status).body(ProblemDetail.forStatusAndDetail(status, "The passkey check failed. Try again."));
    }

    /** Any valid token: customers complained about signing in again just to add a passkey. */
    private long recentlySignedIn(Jwt jwt) {
        return Long.parseLong(jwt.getSubject());
    }
}
```

## Findings

1Any origin accepted

"The Android app and staging send other origins" is solved by listing them. Accepting every origin accepts answers made for a phishing page.

**Test evidence:** `aSignInAnsweredForAPhishingPageIsRefused` fails.

2The sign-in challenge taken from the request

"Random and signed" is true and beside the point: the server must know it issued the challenge and that it was not used. Without the lookup, a recorded sign-in works again, expired challenges work, and a malformed answer becomes a 500 because nothing checks it first.

**Test evidence:** `aSignInCapturedOnceAndSentAgainIsRefused`, `aChallengeExpiresAfterFiveMinutes` and `oddAnswersAre400Or401NeverAnError` fail.

3Any token may add a passkey

A stolen 10-minute token is now enough to plant the attacker's own passkey, which then works for months.

**Test evidence:** `addingAPasskeyNeedsASignInFromTheLastFiveMinutes` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class                  | Fixed version | Flawed version |
|-----------------------------|---------------|----------------|
| `PasskeyContractTest`       | 5 / 5         | 5 / 5          |
| `PasskeyDatabaseTest`       | 4 / 4         | 4 / 4          |
| `PasskeySecurityTest`       | 9 / 9         | 6 / 9          |
| `UncheckedCeremonyTrapTest` | 4 / 4         | 2 / 4          |

The signature check still passes on every one of these answers. That is the whole trap: a valid signature over the wrong thing.
