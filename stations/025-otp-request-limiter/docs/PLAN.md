# Station 025 plan: OTP request limiter

**Problem.** Bots request thousands of OTP SMS for one number. Tijori's limiter checks the count, sends the SMS, then
records the request: 20 requests at the same instant all pass the check. It also counts per server.

**Endpoint.** `POST /otp-requests` (Idempotency-Key header, {"mobile"}) 202 with requestId, masked number, expiry and
attempts left; 429 with Retry-After after 3 in 10 minutes (demo rule); 422 a key reused for another number; 400 bad
number or key. The code never appears in a response or log; the SMS is simulated (50 ms, counted).

**Data.** No database. `OtpLimiter`: per-number deque of times, checked and booked in one `ConcurrentHashMap.compute`.
`OtpService`: per-key `CompletableFuture` via `putIfAbsent`, so duplicates (even simultaneous) share one result; a
refused request's key is released. Numbers normalised (+91, leading 0, spaces). Injectable `Clock`.
Limit: per server instance; across servers needs a shared count (station 125).

**Trap.** `CheckThenActTrapTest`: old limiter lets more than 3 of 20 through; the atomic one exactly 3; two servers 6.

**Tests.** Trap, `OtpContractTest`, `OtpConcurrencyTest` (20 at once -> 3 SMS; 3 numbers x 5), `OtpReplayTest`
(retry, 10 simultaneous copies, key reuse, retry after refusal). Concurrency classes rerun 5 times: stable.

**Review.** review/OtpService.java (books after sending; stores the replay after completion; keeps +91/0 forms
apart) and review/OtpLimiter.java (Retry-After from the newest): 7 of 14 tests fail.

**Practice.** 1: keys expire after 24 h. 2: per-address limit. Design: a shared count across servers.
