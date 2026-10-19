# Station 073 plan: Login with JWT for a fitness app

**Problem.** FitNest kept login sessions in each server's memory; every pod restart or deploy logged members out, and
a member sent to another pod was a stranger there. The first "JWT" fix only base64-decoded the token to read `sub`.

**Endpoints.** `POST /auth/login` {username 1-50, password 1-64}: 200 {accessToken, tokenType "Bearer", expiresIn 900};
401 problem JSON "Wrong username or password" for unknown user and wrong password alike; 400 invalid. `GET /workouts/me`
with `Authorization: Bearer`: the token subject's workouts (simulated data); 401 with `WWW-Authenticate: Bearer` for no,
bad, expired, forged, wrong-issuer or wrong-audience tokens; 403 when the token lacks `workouts:read`.

**Security.** HS256 with one shared key (every pod can verify any pod's token). Decoder: signature with this key and
only HS256, exp/nbf with 60 s skew on the app's Clock, iss, aud. Token: iss, sub, aud, iat, exp = 15 min, scope from the
member's own grants. Stateless, CSRF off (bearer header, no cookies). Everything not listed is denyAll.

**Trap.** `UnverifiedTokenTrapTest`: in-memory sessions are gone after a restart; a signed token works on another pod
with the same key; the old base64-only read trusts a forged-key token, an alg "none" token and a month-old token, and
the real API refuses all three.

**Found while building.** (1) Spring Security 7 adds a `FACTOR_PASSWORD` authority to the Authentication after a
password sign-in; building the scope from `authentication.getAuthorities()` put it into every token. Scope now comes
from the UserDetails' grants. (2) A second decoder built in a test without the app's Clock rejected a fresh token as
expired: the timestamp validator uses the machine's clock unless told otherwise. (3) `JwtClaimValidator` fails when the
claim is missing, so a "not revoked" check on `jti` must be a plain validator (challenge 1). (4) For
`withSecretKey`, HS256 is already the default: removing `.macAlgorithm(HS256)` changed no test; kept to say it.
(5) STATELESS -> IF_REQUIRED changed no test: the bearer filter never stores the context in a session anyway.

**Mutations.** no audience check -> 1; no issuer check -> 1; skew 0 -> 1; validator without the app Clock -> 6;
lifetime 30 days -> 4; scope rule -> authenticated() -> 1; scope from getAuthorities() -> 1; macAlgorithm removed -> 0; IF_REQUIRED -> 0.

**Review.** No issuer/audience check, 30-day tokens, any signed-in member reads workouts: 6 of 16 fail.

**Practice.** 1: logout revokes one token (jti list kept until exp). 2: coach reads trainees (scope + trainee list).
3 (paper): refresh tokens and key rotation with `kid`.
