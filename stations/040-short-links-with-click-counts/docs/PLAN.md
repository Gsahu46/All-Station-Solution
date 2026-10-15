# Station 040 plan: Short links with click counts

**Problem.** Chhotu shortens 300-character tracking links for SMS. Old codes were 4 random characters in a table
with no key, saved with "update if the code exists, else insert": two campaigns got the same code and the second
silently replaced the first.

**Endpoints.** `POST /links` {targetUrl} 201 {code, shortUrl, targetUrl} + Location; 400 not an http(s) address,
blank, too long, unknown field; 503 every attempt collided. `GET /{code}` (7 base62 characters) 302 Location, 404
unknown. `GET /links/{code}/stats` {code, targetUrl, clicks, createdAt}, 404.

**Codes.** 7 base62 characters from SecureRandom (62^7), case-sensitive by design (not normalised). Insert with
ON CONFLICT (code) DO NOTHING; 0 rows = taken, try another (5 attempts). Primary key `links_pkey`, checks
`links_code_base62`, `links_target_web`, `links_clicks_non_negative`.

**Clicks.** Redirect = one lookup + LongAdder increment in memory; @Scheduled flush (5 s) with sumThenReset and one
UPDATE per link; @PreDestroy flush. Limit: unflushed clicks (at most flush-ms worth) are lost on a crash. Stats =
stored + pending on this instance.

**Trap.** `OverwritingCodesTrapTest`: old save lets the second campaign take over; birthday odds (5,000 four-char
codes: 57%); now a forced collision retries and the first link is untouched. Mutations: non-atomic flush -> 1 red;
get-or-put race on a new link's counter -> 1 (needed a direct 200-thread test: through HTTP it was not caught);
no retry -> 1; upsert overwrite -> 2.

**Tests.** Trap; `LinkConcurrencyTest` (1,000 parallel clicks; 2,000 clicks during repeated flushes; first clicks on
50 new links; 200 parallel creates); `LinkDatabaseTest` (named constraints, case-sensitive codes, all attempts collide
-> 503 and nothing overwritten, rollback); `LinkContractTest`.

**Review.** upsert "never fails", 301 "faster", any parseable URI. 5 of 16 fail.

**Practice.** 1: custom codes (409 if taken). 2: expiry, 410 Gone (V2). Design: counting at 10,000 clicks a second
on several servers.
