# Station 075 · Sign in with Google

Working Systems · 0–2 years · Core · SaaS · Types: Security

Spring Boot 4.1.1 · Java 25 · Spring Security 7 oauth2Login · OpenID Connect · authorization code flow with PKCE · Nimbus JOSE. Needs JDK 25 (or 21, see Set up & code). No database and no Docker. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows). A real Google sign-in needs your own Google Cloud client id and secret.

**Simulation:** Google is simulated in the tests: a local server with its own signing key plays Google's discovery, key and token endpoints. The running app is set up for the real Google with a demo client id that Google does not know, so a real sign-in stops at Google's page. Taskloom accounts are demo data in memory.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 19 tests.

# 1 · Understand

## The problem in real life

1.  **Teams want Google**

    Taskloom's customers already have Google accounts and asked to use them instead of yet another password.

2.  **A home-made flow**

    The first version took an ID token from the browser, decoded it and used the email in it. A token that Google had issued to some other app, for the same person, signed them in to Taskloom too.

3.  **The fix**

    The standard code flow, run by Spring Security: the token comes straight from Google to the server, and its signature, issuer, audience, expiry and nonce are all checked before anyone is signed in.

A real Google signature only says Google wrote it. Whether it was written for you is in the audience.

## What are we building?

`GET /oauth2/authorization/google` sends the browser to Google; Google sends it back with a code; Taskloom checks everything and signs the person in to their Taskloom account. `GET /me` shows that account.

## An everyday analogy

A visitor badge from the front desk works only in the building it was printed for, only today, and only if the desk's stamp is real. A badge from the building next door, with the same name on it, does not open this door.

## How it works in 4 steps

1.  **Start**: Taskloom redirects to Google with its client id, a state, a nonce and a PKCE challenge.
2.  **Consent**: the person signs in at Google; Google redirects back with a one-time code and the same state.
3.  **Swap**: Taskloom's server sends the code and the PKCE secret to Google, and receives the ID token directly.
4.  **Check, then link**: signature, issuer, audience, expiry, nonce; then the Taskloom account for that Google id.

Check yourself: the ID token is really signed by Google and really says asha. Why can it still be refused?

Because it may have been issued to a different app (its audience is that app's client id). Any app Asha signs in to receives such a token; if Taskloom accepted it, every one of those apps could sign in to Taskloom as Asha. The trap test `aGoogleTokenMeantForAnotherAppIsRefused` shows it.

## What this station is not

- **No real Google in the tests.** A local stand-in plays Google, with its own key; the checks are Spring's real ones.
- **No passwords.** Taskloom never sees one. Passkeys are station 076.
- **No token for calling Google APIs.** Only sign-in: the access token Google returns is not used.

## Key terms

| Term                   | Simple meaning                                                                                                                   | Everyday example                                    | In this project                   |
|------------------------|----------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|-----------------------------------|
| **OAuth 2.0**          | A way for an app to get a token from another service without seeing your password there.                                         | A hotel giving a cleaner a key card for one floor.  | Google's authorization server     |
| **OpenID Connect**     | OAuth 2.0 plus an ID token that says who signed in.                                                                              | The receptionist's signed note: this guest is Asha. | scope `openid`                    |
| **ID token**           | A signed JWT from Google: who (sub, email), for which app (aud), from whom (iss), until when (exp).                              | A visitor badge printed for one building.           | checked by Spring Security        |
| **Authorization code** | A one-time code Google sends back through the browser; the server swaps it for tokens directly with Google.                      | A cloakroom ticket, exchanged at the counter.       | `/login/oauth2/code/google`       |
| **PKCE**               | A secret made per sign-in: its hash goes to Google first, the secret itself with the code later. A stolen code alone is useless. | Half of a torn ticket, matched at the end.          | `code_challenge`, `code_verifier` |
| **State and nonce**    | Random values that tie Google's answer to this browser's own sign-in, and the ID token to this request.                          | A reference number you check on the reply.          | `state`, `nonce`                  |

# 2 · Build: Spec

## Business problem

**Taskloom** (a fictional team task tool) wants Google sign-in; its home-made flow accepted ID tokens meant for other apps.

## Acceptance criteria

Demo data: asha is already linked to her Google account; meera and kabir are invited. Tests invite their own people.

1.  **Given** a start, **then** a redirect to Google with this app's client id, `openid email profile`, a state, a nonce and an S256 PKCE challenge.
2.  **Given** Google's answer with an ID token for this app, **then** the person is signed in and `GET /me` shows their Taskloom account.
3.  **Given** an ID token for another app, from another issuer, with a bad signature, expired, or with another nonce, **then** `401` and no sign-in.
4.  **Given** a callback with a state this browser did not start, **then** `401`, and Google is never asked for tokens.
5.  **Given** a Google account with no Taskloom account, **then** `403`.
6.  **Given** an invited email that Google has not verified, **then** it is not linked.
7.  **Given** a sign-out without the CSRF token, **then** `403`.

## Requirements

- Accounts are linked by Google's `sub`, which never changes; the email is used only once, to accept an invitation, and only when verified.
- Failed sign-ins do not say which check failed.
- The client secret never reaches the browser.

## Learning objectives

- Explain the authorization code flow with PKCE, state and nonce.
- Name every check on an ID token, and what each one stops.
- Configure `oauth2Login` and link Google identities to local accounts.
- Explain why CSRF protection is back on here, unlike stations 071 to 074.

# 2 · Build: API contract

## Endpoints

| Method | Path                           | Purpose                                                                                                   |
|--------|--------------------------------|-----------------------------------------------------------------------------------------------------------|
| `GET`  | `/oauth2/authorization/google` | Starts sign-in: `302` to Google. Handled by Spring Security.                                              |
| `GET`  | `/login/oauth2/code/google`    | Google's redirect back with `code` and `state`. Handled by Spring Security: `302` to `/me`, or a problem. |
| `GET`  | `/me`                          | The signed-in person's Taskloom account.                                                                  |
| `POST` | `/logout`                      | Signs out; needs the CSRF token. `204`.                                                                   |

## Status codes

| Status    | When                                                                                                                                  |
|-----------|---------------------------------------------------------------------------------------------------------------------------------------|
| 200 / 204 | Account shown / signed out                                                                                                            |
| 302       | To Google at the start; to `/me` after a good sign-in                                                                                 |
| 401       | Not signed in; or the sign-in failed any check (state, token, signature, issuer, audience, expiry, nonce), or was cancelled at Google |
| 403       | Signed in at Google, but no Taskloom account for it; a sign-out without the CSRF token                                                |
| 404       | A sign-in provider other than Google                                                                                                  |

## Captured examples

Captured with curl from the running app on 19 Oct 2026. These stop at the redirect or are refused before Google would be asked, so they need no network. The full sign-in, with Google's answer, runs in the tests against the stand-in. `Date`, connection and standard security headers are left out.

### Case 1: start sign-in

**Why:** to Google, with state, nonce and a PKCE challenge, all new for this sign-in. The session cookie remembers them for the way back.

Request

``` code
GET /oauth2/authorization/google HTTP/1.1
```

Response

``` code
HTTP/1.1 302 
Set-Cookie: JSESSIONID=<session id>; Path=/; HttpOnly
Location: https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=taskloom-demo.apps.googleusercontent.com&scope=openid%20email%20profile&state=RKixNiV2mFK7JyfwpEqfgK1seMmBloZyVH3fy-s1t7M%3D&redirect_uri=http://localhost:8080/login/oauth2/code/google&nonce=FF-KvyspRHPLdJslUt1mljH0Wx039ly3Po66Vkb83EI&code_challenge=uNnUSNdsssTb70ETgGstQJzc1NVsXc2nXI_NwZ7GjSo&code_challenge_method=S256
Content-Length: 0
```

### Case 2: `/me` without signing in

**Why:** `401` and where to start. (Spring also keeps this request in a session, to return to it after sign-in.)

Request

``` code
GET /me HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
Set-Cookie: JSESSIONID=<session id>; Path=/; HttpOnly
Content-Type: application/problem+json
Content-Length: 122

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Sign in with Google at /oauth2/authorization/google.",
  "instance": "/me"
}
```

### Case 3: a provider that is not set up

**Why:** `404`. Spring's default here is a `500`.

Request

``` code
GET /oauth2/authorization/github HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json
Content-Length: 144

{
  "title": "Unknown sign-in provider",
  "status": 404,
  "detail": "Taskloom offers sign-in with Google only.",
  "instance": "/oauth2/authorization/github"
}
```

### Case 4: a callback this browser never started

**Why:** no matching state in its session: `401`, and Google is not asked.

Request

``` code
GET /login/oauth2/code/google?code=4/0Afake&state=made-up HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
Content-Type: application/problem+json
Content-Length: 139

{
  "title": "Sign-in failed",
  "status": 401,
  "detail": "Google sign-in could not be completed. Try again.",
  "instance": "/login/oauth2/code/google"
}
```

### Case 5: sign-out without the CSRF token

**Why:** `403`: a form on another website could send this request with the cookie.

Request

``` code
POST /logout HTTP/1.1
```

Response

``` code
HTTP/1.1 403 
Set-Cookie: JSESSIONID=<session id>; Path=/; HttpOnly
Content-Type: application/problem+json
Content-Length: 94

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This request was refused.",
  "instance": "/logout"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                    | What happens                                                               | Proved by                                                                                                    |
|-------------------------------------------------------------------------|----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| Start                                                                   | Redirect with this app's id, scopes, redirect URI, state, nonce, challenge | `startingSignInRedirectsToGoogleForThisApp`                                                                  |
| A linked member signs in                                                | `/me` shows their account; a parameter chooses nothing                     | `aLinkedMemberSignsInAndSeesTheirAccount`                                                                    |
| First sign-in of an invited email, later a changed Google email         | Linked by email once, then by Google id                                    | `anInvitedEmailIsLinkedAtFirstSignInAndTheGoogleIdAfterThat`                                                 |
| A Google account with no Taskloom account                               | `403`, not signed in                                                       | `aGoogleAccountWithNoTaskloomAccountIs403AndANewSignInIsNotStarted`                                          |
| Not signed in; another provider                                         | `401`; `404`                                                               | `meWithoutSigningInIs401AndAnUnknownProviderIs404`                                                           |
| PKCE, state and nonce                                                   | S256; new for every sign-in; the verifier matches the challenge            | `everySignInGetsItsOwnPkceChallengeStateAndNonce`, `theVerifierSentToGoogleMatchesTheChallengeInTheRedirect` |
| Another browser's state                                                 | `401`, Google never asked                                                  | `aCallbackWithAnotherBrowsersStateIsRefusedBeforeGoogleIsAsked`                                              |
| Another nonce                                                           | `401`                                                                      | `anIdTokenWithAnotherNonceIsRefused`                                                                         |
| An unverified invited email                                             | Not linked; the invitation stays                                           | `anUnverifiedEmailNeverLinksAnInvitation`                                                                    |
| A second Google account with a linked member's email                    | `403`: someone else                                                        | `anotherGoogleAccountWithALinkedMembersEmailDoesNotBecomeThatMember`                                         |
| Sign-in                                                                 | A new session id                                                           | `theSessionIdChangesAtSignIn`                                                                                |
| Sign-out without and with the CSRF token                                | `403`; `204`                                                               | `signingOutNeedsTheCsrfTokenBecauseTheCookieTravelsByItself`                                                 |
| Cancelled consent, SQL-looking state, 5,000 characters, an unknown code | `401`, never an error                                                      | `oddCallbacksAre401NeverAnError`                                                                             |

## The trap

Plausible but wrong

Accepting any ID token without checking issuer and audience.

Each test makes one ID token, shows that the old decode-only check signs in as asha, then lets the stand-in Google hand out exactly that token in a real sign-in:

- **For another app.** Signed by Google, about asha, but its audience is a photo app's client id: `401`.
- **From another issuer.** Same signature key, issuer `https://accounts.evil.example`: `401`.
- **Someone else's key.** Even with Google's key id in the header: `401`.
- **Expired.** Last week's token: `401`.
- **The control.** The same claims, right in every way: signed in.

While building, each part was undone once: no `email_verified` check turned 1 test red; CSRF off 1; no new session id at sign-in 1; no `403` for unknown accounts 2; no handler for unknown providers 1; no lower-casing of emails 1. The explicit PKCE setting turned nothing red and was removed: see Code.

``` code
package com.taskloom.signin;

import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpSession;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Date;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.redirectedUrl;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The home-made flow decoded the ID token and took its email: no signature, no issuer, no audience,
 * no expiry. Each test builds one token it believed, then sends the same token through the real sign-in.
 */
class UncheckedIdTokenTrapTest extends ApiTest {

    static final JsonMapper JSON = JsonMapper.builder().build();

    /** The old check, as it was. */
    static String oldSignedInEmail(String idToken) {
        JsonNode payload = JSON.readTree(Base64.getUrlDecoder().decode(idToken.split("\\.")[1]));
        return payload.get("email").asString();
    }

    /** Sign in through the real flow, with Google's token endpoint handing out exactly this ID token. */
    org.springframework.test.web.servlet.ResultActions signInWith(MockHttpSession browser, java.util.function.Function<String, String> idTokenForNonce) throws Exception {
        var request = start(browser);
        String code = "code-" + java.util.UUID.randomUUID();
        GOOGLE.idTokens.put(code, idTokenForNonce.apply(request.get("nonce")));
        return callback(browser, code, request.get("state"));
    }

    @Test
    void aGoogleTokenMeantForAnotherAppIsRefused() throws Exception {
        // Really signed by Google, really asha: but issued to a photo app she signed in to, which now replays it.
        MockHttpSession browser = new MockHttpSession();
        signInWith(browser, nonce -> {
            String token = GOOGLE.sign(googleClaims("100000000000000000001", "asha@acme.example", nonce).audience("photo-app.apps.googleusercontent.com").build());
            assertThat(oldSignedInEmail(token)).isEqualTo("asha@acme.example");   // the old flow: signed in as asha
            return token;
        }).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.title").value("Sign-in failed"));
        me(browser).andExpect(status().isUnauthorized());
    }

    @Test
    void aTokenFromAnotherIssuerIsRefused() throws Exception {
        MockHttpSession browser = new MockHttpSession();
        signInWith(browser, nonce -> {
            String token = GOOGLE.sign(googleClaims("100000000000000000001", "asha@acme.example", nonce).issuer("https://accounts.evil.example").build());
            assertThat(oldSignedInEmail(token)).isEqualTo("asha@acme.example");
            return token;
        }).andExpect(status().isUnauthorized());
    }

    @Test
    void aTokenSignedWithSomeoneElsesKeyIsRefused() throws Exception {
        RSAKey attacker = new RSAKeyGenerator(2048).keyID("fake-google-1").generate();   // even the same key id
        MockHttpSession browser = new MockHttpSession();
        signInWith(browser, nonce -> {
            String token = FakeGoogle.signWith(attacker, googleClaims("100000000000000000001", "asha@acme.example", nonce).build());
            assertThat(oldSignedInEmail(token)).isEqualTo("asha@acme.example");
            return token;
        }).andExpect(status().isUnauthorized());
    }

    @Test
    void anExpiredTokenIsRefused() throws Exception {
        Instant lastWeek = Instant.now().minus(Duration.ofDays(7));
        MockHttpSession browser = new MockHttpSession();
        signInWith(browser, nonce -> GOOGLE.sign(googleClaims("100000000000000000001", "asha@acme.example", nonce)
                .issueTime(Date.from(lastWeek)).expirationTime(Date.from(lastWeek.plus(Duration.ofHours(1)))).build()))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void theRightTokenSignsIn() throws Exception {
        // The control: the same claims, for this app, from Google, in time.
        MockHttpSession browser = new MockHttpSession();
        signIn(browser, "100000000000000000001", "asha@acme.example").andExpect(status().isFound()).andExpect(redirectedUrl("/me"));
        me(browser).andExpect(status().isOk()).andExpect(jsonPath("$.name").value("Asha Rao"));
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need                  | Version                                                                                                   | Check with      |
|---------------------------|-----------------------------------------------------------------------------------------------------------|-----------------|
| JDK                       | 25 (recommended). JDK 21 also works, see below                                                            | `java -version` |
| Docker                    | Not needed                                                                                                |                 |
| Maven                     | Not needed: the project ships the Maven wrapper                                                           |                 |
| For a real Google sign-in | Your own OAuth client in Google Cloud, with redirect URI `http://localhost:8080/login/oauth2/code/google` |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the app on http://localhost:8080
./mvnw test                 # all 19 tests, against the stand-in Google
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

See where sign-in sends a browser, without following it:

``` code
curl -s -o /dev/null -w '%{redirect_url}\n' http://localhost:8080/oauth2/authorization/google
```

Run it twice: `state`, `nonce` and `code_challenge` change every time. With your own client id and secret in `application.yaml` (or as environment variables), open `http://localhost:8080/oauth2/authorization/google` in a browser: after Google, the sign-in ends in `403` until your Google email is in the invitation list in `Accounts.java`. (Not run while building this station: it needs your own Google client.)

## Troubleshooting

| You see                              | Cause                                                             | Fix                                                                  |
|--------------------------------------|-------------------------------------------------------------------|----------------------------------------------------------------------|
| `redirect_uri_mismatch` at Google    | The redirect URI in Google Cloud differs from Spring's.           | Register exactly `{baseUrl}/login/oauth2/code/google`.               |
| `500` on `/oauth2/authorization/xyz` | Spring's default for an unknown registration id.                  | Set the redirect filter's failure handler, as `SecurityConfig` does. |
| `403` on `POST /logout`              | No CSRF token: protection is on, because the sign-in is a cookie. | Send the token (a form field or the `X-CSRF-TOKEN` header).          |
| `invalid_id_token` in the log        | A claim check failed: issuer, audience, expiry or nonce.          | Fix the configuration (issuer, client id), never the validator.      |

## Project layout

``` tree
stations/075-sign-in-with-google/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/taskloom/signin/
│   ├── SecurityConfig.java   ├── Accounts.java   ├── TaskloomUser.java
│   ├── MeController.java   ├── ProblemResponses.java   └── SignInApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/taskloom/signin/   FakeGoogle.java and the tests
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/taskloom/signin/SecurityConfig.java`

Does  
oauth2Login, the account step, logout and the error answers.

Why  
Spring runs the redirect and the callback; after Spring's ID token checks, the account step links or refuses; `/me` needs a sign-in; everything else refused.

Without it  
A Google account becoming a Taskloom member just by existing, or a sign-out any website can trigger.

- CSRF protection stays on: the sign-in now lives in a session cookie, which the browser sends with any request to this site, including one made by another site's form.
- PKCE: Spring Security 7 sends a challenge for confidential clients too. The explicit `withPkce()` customizer turned no test red when removed, so it is gone. Found while building.
- An unknown provider (`/oauth2/authorization/github`) is a `500` by default; an `ObjectPostProcessor` sets the redirect filter's failure handler to a `404`. Found while building.

#### `src/main/java/com/taskloom/signin/Accounts.java`

Does  
Taskloom accounts and their link to a Google id.

Why  
Linked by `sub`; an invitation is accepted only for a verified email; emails compared lower-case.

Without it  
Account takeover: someone creating a Google account with a member's address, unverified, or a second Google account that shows the same address.

Simulated in memory. `shortcut: lost on restart, one pod only; a real app keeps both maps in its database.`

#### `src/main/java/com/taskloom/signin/TaskloomUser.java`

The signed-in principal: Google's checked identity plus the linked Taskloom account.

#### `src/main/java/com/taskloom/signin/MeController.java`

`/me` from the principal; nothing in the request chooses the account.

#### `src/main/java/com/taskloom/signin/ProblemResponses.java`

One problem shape for 401, 403 and 404. A failed sign-in never says which check failed.

#### `src/main/resources/application.yaml`

The Google client registration. Spring Boot knows Google's endpoints and issuer; the values here are demo values.

#### `src/main/java/com/taskloom/signin/SignInApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                     | Result |
|---------------|-------------------------------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `SignInContractTest` (5)       | pass   |
| Every station | Reproduce the failure before the fix                              | `UncheckedIdTokenTrapTest` (5) | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `SignInSecurityTest` (9)       | pass   |

"Another user's data" here is account takeover: a second Google account with a member's email, or an unverified one, never becomes that member. How the stand-in works: `FakeGoogle` is a JDK HTTP server on a local port with discovery, its public key and a token endpoint; the app finds it through `issuer-uri`, so the token request and every check run for real.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1. No Docker. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 9, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.signin.SignInSecurityTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.signin.SignInContractTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.signin.UncheckedIdTokenTrapTest
[INFO] Tests run: 19, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/taskloom/signin/UncheckedIdTokenTrapTest.java`

Written first: four ID tokens the old check believed, each refused by the real sign-in, and the control.

#### `src/test/java/com/taskloom/signin/SignInSecurityTest.java`

PKCE, state, nonce, account takeover, session fixation, CSRF, odd callbacks.

#### `src/test/java/com/taskloom/signin/SignInContractTest.java`

The redirect, sign-in and linking, `/me`, 401, 403, 404.

#### `src/test/java/com/taskloom/signin/FakeGoogle.java`

The stand-in for Google: discovery, keys, token endpoint, on a local port.

#### `src/test/java/com/taskloom/signin/ApiTest.java`

Shared setup: the app pointed at the stand-in; helpers that walk through a whole sign-in.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/taskloom/signin/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=WorkspaceDomainChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 19 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 22 tests pass (19 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Company accounts only, for Globex

Globex accepts only its own Google Workspace accounts: linking a Globex invitation needs the ID token's `hd` (hosted domain) claim to be `globex.example`. A personal Google account gets `403` and the invitation stays.

**Done when:** the test in `WorkspaceDomainChallengeTest` passes.

Hints

- `user.getClaimAsString("hd")` in the account step; pass it to `Accounts.forGoogle`.
- Check before removing the invitation, so a refused sign-in leaves it for the right account.

#### `challenge/WorkspaceDomainChallengeTest.java`

``` code
package com.taskloom.signin;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpSession;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: Globex allows only its own Google Workspace accounts. Linking an invitation to the Globex workspace
 * needs the ID token's hd (hosted domain) claim to be globex.example; a personal Google account is refused (403)
 * and the invitation stays. Other workspaces are unchanged.
 */
class WorkspaceDomainChallengeTest extends ApiTest {

    @Test
    void globexLinksOnlyItsOwnWorkspaceAccounts() throws Exception {
        String email = "neha-" + java.util.UUID.randomUUID().toString().substring(0, 8) + "@globex.example";
        accounts.invite(email, "Neha", "Globex");
        MockHttpSession personal = new MockHttpSession();
        signIn(personal, newSub(), email).andExpect(status().isForbidden());
        MockHttpSession wrongDomain = new MockHttpSession();
        signIn(wrongDomain, newSub(), email, c -> c.claim("hd", "evil.example")).andExpect(status().isForbidden());
        MockHttpSession workspace = new MockHttpSession();
        signIn(workspace, newSub(), email, c -> c.claim("hd", "globex.example")).andExpect(status().isFound());
        me(workspace).andExpect(jsonPath("$.workspace").value("Globex"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Members list for admins

`GET /workspace/members`: the names of the signed-in members of the caller's own workspace, for workspace admins only (demo rule: asha administers Acme). Others get `403`.

**Done when:** both tests in `WorkspaceAdminChallengeTest` pass.

Hints

- Give the principal `ROLE_ADMIN` when the account is an admin, and add a `hasRole("ADMIN")` rule.
- The workspace comes from the signed-in account, never from the request.

#### `challenge/WorkspaceAdminChallengeTest.java`

``` code
package com.taskloom.signin;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpSession;

import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /workspace/members lists the names of the signed-in members of the caller's own workspace,
 * for workspace admins only (demo rule: asha is Acme's admin). Other members get 403; nobody sees another workspace.
 */
class WorkspaceAdminChallengeTest extends ApiTest {

    @Test
    void anAdminSeesTheirOwnWorkspaceOnly() throws Exception {
        String other = "lena-" + java.util.UUID.randomUUID().toString().substring(0, 8) + "@initech.example";
        accounts.invite(other, "Lena", "Initech");
        signIn(new MockHttpSession(), newSub(), other);
        MockHttpSession asha = new MockHttpSession();
        signIn(asha, "100000000000000000001", "asha@acme.example");
        mvc.perform(get("/workspace/members").session(asha)).andExpect(status().isOk())
                .andExpect(jsonPath("$", hasItem("Asha Rao"))).andExpect(jsonPath("$", not(hasItem("Lena"))));
    }

    @Test
    void aMemberWhoIsNotAnAdminIs403() throws Exception {
        String email = invite("Tara");
        MockHttpSession tara = new MockHttpSession();
        signIn(tara, newSub(), email);
        mvc.perform(get("/workspace/members").session(tara)).andExpect(status().isForbidden());
        mvc.perform(get("/workspace/members")).andExpect(status().isUnauthorized());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A mobile app, and signing out everywhere

Taskloom's phone app cannot keep a client secret: anything shipped in an app can be read. Design its sign-in as a public client (PKCE only, the system browser, a custom redirect URI). Then: when a company disables an employee in Google Workspace, how does Taskloom find out? Compare short Taskloom sessions with OpenID Connect back-channel logout.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: tokens the decode-only check believed.
2.  Build a stand-in Google for the tests, so every step is real HTTP and real validation.
3.  Configure `oauth2Login`; let Spring run the flow and the ID token checks.
4.  Add the account step: link by `sub`, accept invitations for verified emails only.

## Design alternatives and trade-offs

| Approach                                                          | What it costs                                                                    | Verdict                  |
|-------------------------------------------------------------------|----------------------------------------------------------------------------------|--------------------------|
| Code flow with PKCE via Spring's oauth2Login; session cookie      | A session per user; CSRF protection needed.                                      | Chosen                   |
| Decode an ID token sent by the browser                            | Any token for any app signs people in.                                           | The trap                 |
| Verify an ID token sent by the browser (signature, iss, aud, exp) | Fine for a mobile app with Google's SDK; no nonce tied to this server's request. | Valid with every check   |
| Link accounts by email                                            | Simple; emails change and can be reused.                                         | Takeover risk            |
| A broker (Keycloak, Auth0, Cognito) in front of Google            | One more system; many providers and enterprise SSO for free.                     | When more providers come |

## Database design

No database in this station: accounts and links are demo data in memory. In a real app: a `google_links` table with `sub` as a unique key and the account id, and invitations with a unique lower-case email. The link is the thing that must never be guessed from an email.

# 3 · Go deeper: Production

The client secret  
From a secret store, never the repository (the one here is a demo value). Register the exact redirect URIs only.

Cookies  
Captures show the session cookie with `HttpOnly` only, because the demo runs on plain HTTP. In production: HTTPS, `server.servlet.session.cookie.secure=true` and a `SameSite` setting.

Several pods  
The sign-in in progress (state, nonce, PKCE verifier) and the session live in one pod's memory. Use sticky sessions or Spring Session with a shared store.

Logs  
Never log codes, tokens or the client secret.

Standards  
OAuth 2.0 is RFC 6749 and PKCE RFC 7636 (both Proposed Standards); OpenID Connect Core 1.0 is an OpenID Foundation final specification; the OAuth 2.0 Security Best Current Practice is RFC 9700 (BCP 240).

# 3 · Go deeper: Interview

## Interview takeaways

What is the difference between OAuth 2.0 and OpenID Connect?

OAuth 2.0 gives an app an access token to call an API. OpenID Connect adds an ID token that says who signed in, and rules for checking it. Sign-in needs OpenID Connect.

Which checks does an ID token need?

Signature with the provider's published key, issuer equal to the provider, audience containing this app's client id, not expired, and the nonce this app sent.

Why PKCE if the server has a client secret?

It ties the code to the sign-in that asked for it: a code stolen from a redirect cannot be swapped by anyone who does not hold the verifier. Current guidance asks for it for every client.

What do state and nonce protect?

State ties Google's redirect to this browser's own sign-in (no one can make you finish theirs). Nonce ties the ID token to this request (no replay of an old token).

Why link by sub and not by email?

sub is Google's permanent id for the account. Emails change, can be unverified, and an address can later belong to someone else.

## Self-check rubric

| Area        | Meets the bar                           | Above the bar                                          |
|-------------|-----------------------------------------|--------------------------------------------------------|
| Correctness | All 19 tests pass.                      | You ran the flawed version and explained each failure. |
| Flow        | Code flow through Spring's oauth2Login. | You can say what state, nonce and PKCE each stop.      |
| Tokens      | All five ID token checks.               | A test for each, through a stand-in provider.          |
| Accounts    | Linked by sub.                          | No takeover through unverified or reused emails.       |

# 3 · Go deeper: Review

## The pull request

A teammate fixes three tickets at once: staging sign-ins failing with `invalid_id_token` ("the signature is what matters"), the web app getting `403` on sign-out, and members who switched Google accounts losing their Taskloom account. Read the two files and list every problem before opening the findings.

#### `review/SecurityConfig.java`

``` code
package com.taskloom.signin;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.security.config.ObjectPostProcessor;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.oauth2.client.oidc.authentication.OidcIdTokenDecoderFactory;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserRequest;
import org.springframework.security.oauth2.client.registration.ClientRegistration;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserService;
import org.springframework.security.oauth2.client.web.OAuth2AuthorizationRequestRedirectFilter;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.security.oauth2.jwt.JwtDecoderFactory;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.logout.HttpStatusReturningLogoutSuccessHandler;

@Configuration
class SecurityConfig {

    /**
     * Sign-in with Google's authorization code flow. Spring Security's filters handle /oauth2/authorization/google
     * (the redirect to Google) and /login/oauth2/code/google (Google's redirect back). The session cookie then carries
     * the sign-in. The redirect carries state, nonce and a PKCE challenge: Spring Security 7
     * adds PKCE for every client, including confidential ones like this.
     */
    @Bean
    SecurityFilterChain web(HttpSecurity http, ProblemResponses problems,
                            OAuth2UserService<OidcUserRequest, OidcUser> users) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.GET, "/me").authenticated()
                        .requestMatchers("/error").permitAll()
                        .anyRequest().denyAll())
                .oauth2Login(o -> o
                        .userInfoEndpoint(u -> u.oidcUserService(users))
                        .defaultSuccessUrl("/me", true)
                        .failureHandler(problems::signInFailed)
                        // Spring answers an unknown provider (/oauth2/authorization/github) with a 500 by default.
                        .withObjectPostProcessor(new ObjectPostProcessor<OAuth2AuthorizationRequestRedirectFilter>() {
                            @Override
                            public <F extends OAuth2AuthorizationRequestRedirectFilter> F postProcess(F filter) {
                                filter.setAuthenticationFailureHandler(problems::unknownProvider);
                                return filter;
                            }
                        }))
                .logout(l -> l.logoutSuccessHandler(new HttpStatusReturningLogoutSuccessHandler(HttpStatus.NO_CONTENT)))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .csrf(c -> c.disable());   // the web app kept getting 403 on sign-out
        return http.build();
    }

    /**
     * Staging sign-ins failed with "invalid_id_token" (issuer mismatch). The signature is checked against Google's
     * keys anyway, so only the expiry is validated here.
     */
    @Bean
    JwtDecoderFactory<ClientRegistration> idTokenDecoderFactory() {
        OidcIdTokenDecoderFactory factory = new OidcIdTokenDecoderFactory();
        factory.setJwtValidatorFactory(registration -> new JwtTimestampValidator());
        return factory;
    }

    /**
     * Runs after Spring has checked the ID token. Then: which Taskloom account is this? No account, no sign-in.
     */
    @Bean
    OAuth2UserService<OidcUserRequest, OidcUser> users(Accounts accounts) {
        OidcUserService google = new OidcUserService();
        return request -> {
            OidcUser user = google.loadUser(request);
            return accounts.forGoogle(user.getSubject(), user.getEmail(), user.getEmailVerified())
                    .map(account -> new TaskloomUser(user, account))
                    .orElseThrow(() -> new OAuth2AuthenticationException(new OAuth2Error(Accounts.NOT_INVITED)));
        };
    }
}
```

#### `review/Accounts.java`

``` code
package com.taskloom.signin;

import org.springframework.stereotype.Component;

import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Taskloom's own accounts, and which Google account (by its stable subject id, "sub") each is linked to.
 * Simulated: held in memory. shortcut: lost on restart, one pod only; a real app keeps both maps in its database.
 */
@Component
class Accounts {

    record Account(String id, String name, String email, String workspace) {
    }

    static final String NOT_INVITED = "not_invited";

    /** Google sub -> account. asha linked her Google account last week. */
    private final Map<String, Account> linked = new ConcurrentHashMap<>(Map.of(
            "100000000000000000001", new Account("acc-1", "Asha Rao", "asha@acme.example", "Acme")));

    /** Invited by a workspace admin, not yet signed in: lower-case email -> account waiting to be linked. */
    private final Map<String, Account> invited = new ConcurrentHashMap<>(Map.of(
            "meera@acme.example", new Account("acc-2", "Meera Iyer", "meera@acme.example", "Acme"),
            "kabir@globex.example", new Account("acc-3", "Kabir Shah", "kabir@globex.example", "Globex")));

    /** What the workspace admin's invite screen calls (the screen is not part of this station). */
    void invite(String email, String name, String workspace) {
        String key = email.toLowerCase(Locale.ROOT);
        invited.put(key, new Account("acc-" + UUID.randomUUID(), name, key, workspace));
    }

    /**
     * The account for this Google sign-in: by sub if already linked, else by email, so people who switch Google
     * accounts keep their Taskloom account.
     */
    Optional<Account> forGoogle(String sub, String email, Boolean emailVerified) {
        Account account = linked.get(sub);
        if (account != null || email == null) {
            return Optional.ofNullable(account);
        }
        String key = email.toLowerCase(Locale.ROOT);
        Account byEmail = linked.values().stream().filter(a -> a.email().equals(key)).findFirst().orElseGet(() -> invited.remove(key));
        if (byEmail != null) {
            linked.put(sub, byEmail);
        }
        return Optional.ofNullable(byEmail);
    }
}
```

## Findings

1The ID token validator checks only the expiry

"Issuer mismatch on staging" was a configuration problem; replacing the validator removes the issuer and audience checks for everyone. Any app's Google token for a person now signs them in here: the original incident.

**Test evidence:** `aGoogleTokenMeantForAnotherAppIsRefused` and `aTokenFromAnotherIssuerIsRefused` fail.

2CSRF protection turned off

The sign-in is a session cookie now: any website can make a visitor's browser post to Taskloom with it.

**Test evidence:** `signingOutNeedsTheCsrfTokenBecauseTheCookieTravelsByItself` fails.

3Accounts found by email, verified or not

"People who switch Google accounts" can also be people who create one with someone else's address. Any Google account showing a member's email becomes that member, and unverified emails accept invitations.

**Test evidence:** `anotherGoogleAccountWithALinkedMembersEmailDoesNotBecomeThatMember` and `anUnverifiedEmailNeverLinksAnInvitation` fail.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class                 | Fixed version | Flawed version |
|----------------------------|---------------|----------------|
| `SignInContractTest`       | 5 / 5         | 5 / 5          |
| `SignInSecurityTest`       | 9 / 9         | 6 / 9          |
| `UncheckedIdTokenTrapTest` | 5 / 5         | 3 / 5          |

Each ticket was real. The expired-token, forged-key and nonce tests still pass on the flawed version: the signature and expiry are still checked, which is exactly why the missing audience check is easy to miss.
