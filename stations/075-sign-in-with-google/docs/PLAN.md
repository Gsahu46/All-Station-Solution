# Station 075 plan: Sign in with Google

**Problem.** Taskloom teams want Google sign-in. The home-made flow decoded the ID token it was given and took the
email from it: a Google token issued to another app (or by another issuer, or expired) signed people in.

**Endpoints.** `GET /oauth2/authorization/google`: 302 to Google with response_type=code, client_id, scope openid email
profile, redirect_uri, state, nonce, PKCE S256 challenge. `GET /login/oauth2/code/google` (Google's redirect back,
handled by Spring): token request with code_verifier, ID token checked (signature from Google's keys, iss, aud,
exp, nonce), then the Taskloom account: 302 to /me; 401 for any failed check; 403 for a Google account with no
Taskloom account. `GET /me`: the linked account; 401 without sign-in. `POST /logout` with CSRF token: 204. An
unknown provider: 404 (Spring's default is a 500).

**Linking.** By Google `sub` once linked; first sign-in links an invited email only when `email_verified`; a second
Google account showing a linked member's email is someone else (403).

**Security.** Session cookie after sign-in, so CSRF stays on; session id changes at sign-in. Simulated Google in tests:
a JDK HttpServer with discovery, JWKS (RSA 2048) and token endpoint, so every step is real HTTP and real validation.

**Trap.** `UncheckedIdTokenTrapTest`: the old decode-only check believes a token for another app, from another issuer,
signed with another key (same kid), and an expired one; the real flow refuses each; the right token signs in.

**Found while building.** (1) Spring Security 7 sends a PKCE challenge for confidential clients by default: the
explicit `withPkce()` customizer changed no test and was removed. (2) `/oauth2/authorization/{unknown}` is a 500 by
default (the redirect filter's failure handler); set through an ObjectPostProcessor to a 404. (3) An unauthenticated
GET /me creates a session (the request cache saves it for after sign-in).

**Mutations.** no email_verified check -> 1; CSRF off -> 1; session fixation none -> 1; no 403 mapping -> 2; no
404 handler -> 1; no lower-casing -> 1; PKCE customizer removed -> 0 (default).

**Review.** ID token validator replaced by expiry only ("issuer mismatch on staging"), CSRF off, link by email
without email_verified: 5 of 19 fail.

**Practice.** 1: Globex links only Google Workspace accounts with hd=globex.example. 2: GET /workspace/members for
workspace admins (ROLE_ADMIN), own workspace only. 3 (paper): a mobile app (public client, PKCE only) and back-channel
logout.
