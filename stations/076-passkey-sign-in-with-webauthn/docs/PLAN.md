# Station 076 plan: Passkey sign-in with WebAuthn

**Problem.** Tijori customers lost money to phished passwords and SIM-swapped SMS codes (14 accounts). Passkeys:
a key pair per site on the customer's device, unlocked with a fingerprint or face; nothing to type into a fake page.

**Endpoints.** `POST /2fa/totp` {email, password, code}: the fallback, both factors at once; 200 token (amr pwd otp mfa);
401 one answer. `POST /webauthn/registration/options` (token from the last 5 minutes, else 403): challenge, rp, user
(random 32-byte handle), ES256/RS256, residentKey and userVerification required, excludeCredentials.
`POST /webauthn/registration` {label, credential}: 201; a failed check 400. `POST /webauthn/authentication/options`:
challenge, rpId, no allowCredentials. `POST /webauthn/authentication` {credential}: 200 token (amr hwk user); 401 for
any failed check. `GET /accounts/me`: simulated balance in paise. (An authentication-options endpoint is added: a
sign-in needs a challenge from somewhere.)

**Checks.** The challenge is looked up and used up in one conditional UPDATE (ours, unused, unexpired, right purpose,
right customer); webauthn4j then checks it against clientDataJSON with our origin and our rp id, user verification,
the signature, the counter. The server compares userHandle with the passkey's customer (not covered by the signature).
TOTP RFC 6238, current and previous step, each code once (totp_last_step < step).

**Database.** customers (email lower/unique, user handle 32 bytes unique, bcrypt shape, TOTP secret >= 20 bytes,
balance >= 0); passkeys (credential id length, sign count 0..2^32-1, label length); webauthn_challenges (32 bytes,
purpose, registration needs a customer, at most 5 minutes, used after created). Ceremonies are transactions with
noRollbackFor CeremonyFailed: a failed check uses the challenge up, a failed save rolls back.

**Trap.** `UncheckedCeremonyTrapTest`: the old signature-only check accepts a replayed sign-in, a sign-in answered for
a phishing origin, and stores a passkey made for another rp id; the API refuses each; the control signs in.

**Found while building.** (1) With the challenge check removed, the replay test first stayed green: the emulator's
counter rose, and the counter check refused the replay. Synced passkeys commonly report 0, so the test device now
keeps 0 and a security-key device counts. (2) The emulator always reports user verification, so no test proves the UV
requirement (it is passed as required to webauthn4j). (3) The signature does not cover userHandle: changing it keeps
the signature valid, so the server must compare it. (4) In the review version the client challenge is decoded
outside any check, so a malformed answer is a 500.

**Mutations.** challenge from the request -> 3; any origin -> 1; no userHandle check -> 1; no owner filter on the
registration challenge -> 1; UV not required -> 0 (emulator); no transaction on registration -> 1; rollback on every
failure -> 1; no recent sign-in check -> 1; TOTP code reusable -> 2; no previous-step window -> 1; counter not stored -> 1.

**Review.** Any origin ("Android app and staging"), sign-in challenge taken from clientData ("random, signed"), any
token may add a passkey: 5 of 22 fail.

**Practice.** 1: list and remove own passkeys (404 for others'). 2: lock code sign-in after 5 wrong codes for 15
minutes (V3; used codes do not count). 3 (paper): account recovery without SMS, and Android/iOS origins.
