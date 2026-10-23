# Station 100 plan: Expiring unpaid hotel holds

**Problem.** Ghoomo (fictional hotel booking): a guest holds a room while paying; unpaid holds blocked rooms for
days, and when a second server was added, the clean-up job ran on both at once and gave rooms back twice, so the
hotel was overbooked.

**Endpoints.** `POST /holds {roomTypeId, date, guestEmail}` with `Idempotency-Key` (8 to 64 of A-Z a-z 0-9 -): 201,
Location, the hold (no guest details); the same key and request again 200, the same hold; the same key with another
request 422; no free room 409; no such room night 404; bad input 400. `GET /holds/{id}`: the hold; 404.

**Rules.** room_nights (room type, night, total, held) with CHECK held BETWEEN 0 AND total. Taking a room is one
UPDATE ... WHERE held < total, in the same transaction as the hold. A hold lasts 15 minutes (demo rule; one night per
hold). E-mails lower-cased with Locale.ROOT for the request hash.

**Expiry.** @Scheduled fixed delay 30 s, on every server. One transaction: UPDATE holds SET EXPIRED WHERE id IN (due,
HELD, LIMIT 500 FOR UPDATE SKIP LOCKED) AND status = 'HELD' RETURNING the room night; then held - 1 for each. A
hold is expired, and its room given back, once, whoever runs the job and however often.

**Trap.** `DoubleExpiryTrapTest`: the old job (read due holds, then give back and mark) on two servers that both read
first: one expired hold, two rooms back, six guests in five rooms. The API's job on two servers: one room back, the
sixth guest 409.

**Tests.** A test clock; the job off and run by the tests; one test with the real schedule (Awaitility).

**Review.** The old job's shape, with a lock in Java (synchronized) "so it never runs twice".

**Practice.** 1: POST /holds/{id}/confirmation. 2: DELETE /holds/{id}, giving the room back once. 3 (paper): jobs
that must run on exactly one server (ShedLock, leader election, a queue).
