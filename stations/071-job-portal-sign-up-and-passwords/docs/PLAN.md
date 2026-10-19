# Station 071 plan: Job portal sign-up and passwords

**Problem.** Hireloop stored passwords as unsalted MD5; a leak exposed 80,000 accounts, because one fast hash per
guess lets a common-password list crack them at once.

**Endpoints.** `POST /candidates/signup` {email, fullName, password}: email lower-cased (Locale.ROOT), password 12-64
characters and at most 72 UTF-8 bytes (bcrypt's limit); 201 {id, email, fullName}, Location /candidates/me; 409
duplicate email in any case; 400 invalid. `GET /candidates/me` with HTTP Basic: the signed-in candidate only; 401
problem JSON without or with wrong credentials (identical for unknown email and wrong password).

**Security.** SecurityFilterChain: sign-up open, everything else authenticated; Basic, stateless, CSRF off (no cookies,
nothing for a browser to send by itself); CORS only for https://app.hireloop.example (bean must be named
corsConfigurationSource). PasswordEncoder: DelegatingPasswordEncoder with bcrypt for new hashes and {MD5} only to
verify imported hashes; CandidateAccounts is a UserDetailsPasswordService, so Spring re-hashes a legacy password with
bcrypt at the first good sign-in. Spring's default delegating list also accepts {noop} plain text: not used.

**Database.** candidates_password_hash_shape (a bcrypt hash of cost 10-31, or a legacy {MD5} digest; plain text, bare
digests and {noop} refused), candidates_email_lower, candidates_email_unique. Two legacy accounts with MD5 hashes.

**Trap.** `FastHashTrapTest`: an MD5 leak is cracked from a 25-password list; a bcrypt hash of the same password
reveals nothing and only the real password verifies; a legacy account is upgraded to bcrypt at first sign-in.

**Found while building.** (1) A CorsConfigurationSource bean named anything but corsConfigurationSource is silently
ignored: every origin got through. (2) Spring Security 7.1 still ships MD5 in PasswordEncoderFactories' list, along
with {noop}. (3) Without an encoder for {MD5}, a legacy row makes sign-in fail with a 500, which also breaks "unknown
and wrong look the same". (4) A password of 30 rupee signs is 30 characters but 90 bytes: past bcrypt's 72.

**Mutations.** no MD5 verifier -> 2; no upgrade service -> 1; no byte check -> 1; no lower-casing -> 2; no hash CHECK
-> 1; CORS bean misnamed -> 1.

**Review.** SHA-256 unsalted encoder, 6-character minimum, email kept as typed, CORS "*": 8 of 14 fail.

**Practice.** 1: change password (current password again). 2: lock after 5 wrong passwords for 15 minutes.
3 (paper): breached-password checks (k-anonymity range API) and argon2.
