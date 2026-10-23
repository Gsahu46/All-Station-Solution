# Station 096 plan: Partner API keys and quotas

**Problem.** Mapwise (fictional maps company): one partner's bug sent 3 million requests in an hour, and because
the API had one limit for everyone, every partner's requests slowed down or were refused.

**Endpoints.** `GET /geocode?address` with `X-Api-Key`: 200 a place from a fixed list (simulated geocoder), 404 not
found, 400 under 3 or over 200 characters or control characters. `GET /partners/{id}/usage`: the partner's plan and
what is left; another partner's id 403.

**Keys.** A servlet filter before every controller: no key 401; a key in the URL (?api_key=) 401 with a message,
never read; unknown 401; suspended 403. Keys are looked up by SHA-256 (only hashes are in configuration).

**Limits.** Per partner: a token bucket (burst, refilled at per-second) and a daily quota per UTC day, both in the
partner's own bucket object, synchronized. 429 with Retry-After (whole seconds) and the reason. Only answered
requests count against the day. Demo plans: Zoomkart 5/s, burst 10, 100,000 a day; Chalo (trial) 1/s, burst 3, 20 a
day; Old Maps suspended. In memory, per server (shortcut: shared store for more than one server).

**Trap.** `GlobalLimitTrapTest`: one bucket for the whole API, Zoomkart's 50 requests leave Chalo refused; with
per-partner buckets Zoomkart gets its 10 and Chalo is unaffected.

**Tests.** A clock moved by hand (each test on a new day). 100 parallel requests through MockMvc; 8 threads and
20,000 takes on the bucket itself.

**Review.** A fixed one-second window instead of a bucket, and refused requests counted against the day.

**Practice.** 1: X-RateLimit-Remaining and X-Quota-Remaining headers. 2: POST /geocode/batch costing one request per
address, all or nothing. 3 (paper): the same limits across six servers.
