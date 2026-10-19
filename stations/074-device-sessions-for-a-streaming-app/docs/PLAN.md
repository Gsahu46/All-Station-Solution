# Station 074 plan: Device sessions for a streaming app

**Problem.** Streamo's refresh token lived a year, was stored as it is and never changed; a copy taken from a shared
laptop kept working for months, and "log out of all devices" only refreshed the screen.

**Endpoints.** `POST /auth/login` {email, password, deviceName, deviceType phone|tv|web}: 200 {accessToken (10 min),
refreshToken, tokenType, expiresIn 600, deviceId}; 401 one answer; 400 invalid. `POST /auth/refresh` {refreshToken, 43
base64url chars}: 200 new pair; 401 "Sign in again on this device" for unknown, expired, used or signed-out; 400 bad
shape. `POST /auth/logout` (bearer): 204, this device only. `GET /me/devices`: own active devices, `current` marked.
`DELETE /me/devices/{id}`: 204; unknown or another member's: 404; not a UUID: 400. Devices need scope `devices`
(a TV gets `playback` only: 403).

**Security.** HS256 access JWT with sub, sid (device session), scope, iss, aud; decoder checks signature, HS256, exp
(30 s skew), iss, aud and that the device session is still active (one indexed lookup per request, so removal is
immediate). Refresh tokens: 32 SecureRandom bytes, SHA-256 stored, 30 days, rotated on every use by one conditional
UPDATE ... RETURNING; a used token presented again ends the device session (reason reuse) for both holders.

**Database.** members (email lower/unique, bcrypt shape), device_sessions (type, name length, reason list, revoked_at
and reason together), refresh_tokens (hash shape, expiry at most 30 days, used after created, partial unique index
refresh_tokens_one_live_per_session).

**Trap.** `NeverRotatingTokenTrapTest`: the old store keeps a stolen token working after "log out of all devices";
the real API ends the device when the copy is used after the owner rotated, and also when the thief was first;
removing a device stops its access token at once; only hashes are stored.

**Found while building.** (1) Without @Transactional on refresh, the parallel test got no winner at all: the
first UPDATE committed alone, a loser saw the used token and ended the session before the winner's second step. (2)
Ten parallel refreshes with one token end the device: the safe side of a race, and a real cost for a phone that
retries after a timeout (a short grace window is the usual softening; not built). (4) The first run against the real app failed every
sign-in: created_at and expires_at came from two clock reads, so the token was 30 days and 1 microsecond and the
expiry CHECK refused it; the frozen test clock hid it. Clock read once; the test clock can now step per read. (5) Under
denyAll that server error was forwarded to /error and shown as a 401: /error is permitted. (3) Devices signed in within the
same instant sort by random id: tests move the clock.

**Mutations.** token reusable (no used_at check) -> 3; no session end on reuse -> 3; no active-session check in the
decoder -> 2; no member in the DELETE query -> 1; TV gets devices scope -> 1; refresh without transaction -> 2.

**Review.** Refresh token kept for 30 days without rotation, no per-request session check, DELETE by id only.

**Practice.** 1: sign out every other device (DELETE /me/devices). 2: at most 5 devices, the least recently used is
signed out (reason 'limit', V3 migration, member row lock). 3 (paper): a grace window for retries and binding
refresh tokens to the device (DPoP, RFC 9449).
