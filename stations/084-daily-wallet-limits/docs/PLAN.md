# Station 084 plan: Daily wallet limits

**Problem.** Tijori (fictional wallet app): two top-ups at the same second took a minimum-KYC wallet past its
₹10,000 daily limit. Each request summed today's top-ups, saw room, and inserted.

**Endpoint.** `POST /wallets/{id}/top-ups` {amountPaise, ₹1 to ₹1,00,000}: 201 with the top-up, the new balance,
today's total and the limit; over the limit 409 with how much is left (`remainingTodayPaise`); unknown wallet 404;
a fraction, a missing amount or out of range 400. Nothing is charged: a record is created and a balance number rises.

**Locking.** One transaction: `SELECT ... FROM wallets ... FOR UPDATE` (the parent row), then sum today's top-ups,
then insert and raise the balance. A second top-up for the same wallet waits at the lock and sums again after the
first commits. Other wallets do not wait.

**Day.** The IST calendar day: [00:00 IST, next 00:00 IST), which is 18:30 UTC the evening before.

**Database.** kyc_tiers (daily limit > 0), wallets (tier FK, balance >= 0), top_ups (amount > 0, wallet FK). Trigger
`top_ups_within_daily_limit` (BEFORE INSERT) locks the wallet row and sums the IST day, so plain SQL writers are held
to the limit too. Limits: inserts only; later amount or tier changes are not checked.

**Trap.** `UnlockedSumTrapTest`: two real transactions, step by step, trigger disabled. Without a lock both sum ₹0
and both insert ₹6,000. With the wallet locked, the second waits and then sums ₹6,000.

**Found while building.** (1) `NumberFormat` for en-IN prints 100,000.00: DecimalFormat keeps one grouping size, so
₹1,00,000.00 is grouped by hand (tested). (2) With the database rule in place, the missing Java lock shows as a
500 from the rule, not as an over-limit total: the concurrency test counts statuses.

**Mutations.** no wallet lock -> 1; UTC day -> 2; >= limit -> 2; no trigger -> 4; trigger without lock -> 1;
trigger in UTC -> 2; no transaction -> 2; balance not raised -> 3.

**Review.** Locks the top-up rows it sums ("only what we read") and takes the day from the UTC clock: 3 of 15 fail.

**Practice.** 1: GET limits (left today, resets at). 2: reversal of a top-up whose money never arrived (V3 adds
reversed_at; the rule skips reversed rows). 3 (paper): monthly and yearly limits, and tier changes mid-day.
