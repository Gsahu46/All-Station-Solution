# Station 072 plan: Password reset by email

**Problem.** Hireloop's reset links never expired, worked any number of times, were stored as plain text, and the
form said "No account found with this email" for unknown addresses: a free account-existence checker.

**Endpoints.** `POST /password-resets` {email}: always 202 with one message; a link is created only for an ACTIVE
account with fewer than 3 open links (demo rule), and an email row is written to outbox_emails (simulated, nothing
sent). `POST /password-resets/{token}/complete` {newPassword 12-64, <= 72 bytes}: 204; unknown, used and expired links
all get the same 400. `GET /candidates/me` (Basic): 200; suspended accounts 403; 401 otherwise.

**Tokens.** 32 bytes from SecureRandom, base64url (43 characters). Only SHA-256 of the token is stored (fine for 256
random bits, unlike passwords). Completing is one UPDATE ... SET used_at WHERE hash AND unused AND unexpired
RETURNING candidate_id: single use even when used twice at once. Then the password changes and every other open link
of that account is deleted. Clock bean; tests move a test clock forward.

**Database.** password_resets_token_hash_shape (64 hex), _unique, _expiry (at most 1 hour), _used_in_time, _candidate_fk
(cascade); candidates_password_hash_shape (bcrypt only). Demo hashes made with pgcrypto crypt(..., gen_salt('bf', 10)),
which Spring's BCryptPasswordEncoder reads.

**Trap.** `ReusableTokenTrapTest`: the old form's two replies differ, the new ones are byte-identical; an old token is
readable in its table and still works after 31 days; a new link works once, not after 31 minutes, and the table holds
only its hash.

**Mutations.** reply differs for unknown -> 3; no expiry check -> 1; reusable link -> 2; other links kept -> 1; no
flood limit -> 1; token stored in clear -> 9 (the hash CHECK refuses it, so every request fails).

**Review.** 404 for unknown emails, link not marked used, other links kept, no flood limit: 7 of 17 fail.

**Found while building.** A challenge solution adding /candidates/me/password got 403: the chain ends in denyAll, so
every new path must be listed.

**Practice.** 1: "your password was changed" notice. 2: change password (signed in) also cancels open links.
3 (paper): sessions and tokens issued before a reset.
