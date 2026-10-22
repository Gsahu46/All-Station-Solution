# Station 082 plan: Movie seat holds

**Problem.** SeatSure sold seat F12 twice for one show. The first fix locked seats and called the payment provider
inside the lock, with no lock timeout: a slow provider made everyone else wait.

**Endpoints.** `POST /shows/{id}/holds` {customer, seats: [..] or count: n, at most 6}: 201 with id, seats, total in
paise, expiresAt (10 minutes); a seat taken 409 naming it; unknown show or seat 404; a seat locked by someone else for
longer than the lock timeout (2 s) 503 with Retry-After: 1; both or neither of seats/count 400. `POST
/holds/{id}/confirm`: charges (simulated, idempotent by hold id) with no lock held, then one UPDATE books the seats if
this hold still owns them; 200; a second confirm answers the same; expired before paying 409; seats re-held by
someone else after the hold ran out: refunded (simulated) and 409.

**Locking.** Named seats: SELECT ... FOR UPDATE in a short transaction with set_config('lock_timeout') (SET LOCAL).
Any seats: FOR UPDATE SKIP LOCKED, so parallel pickers neither wait nor collide.

**Database.** seats (PK show+seat, seat number shape, price > 0, hold id and end together, a booked seat is not
held); holds (status, total > 0, 1-6 seats, confirmed or refunded holds carry a payment reference).

**Trap.** `LockAcrossPaymentTrapTest`: a transaction holding F12 for 3 s (the old confirm) no longer makes the API
wait: 503 within the timeout; and the API's own confirm pays with no lock, so F12 is answered 409 at once and F13 is
not blocked.

**Found while building.** (1) Spring 7 reports PostgreSQL's lock timeout (SQLState 55P03) as UncategorizedSQLException,
not CannotAcquireLockException: matched by SQLState. (2) The first parallel tests passed with FOR UPDATE and SKIP
LOCKED removed: the race window was too small. A 200 ms trigger on holds (as on a busy database) makes it wide; now
both mutations turn red. (3) The confirm's `held_until > now` condition changed no test: hold_id already changes when
someone else takes the seat; removed. (4) expiresAt came back in nanoseconds on create and microseconds after a
read: the clock is truncated to microseconds.

**Mutations.** no FOR UPDATE -> 1; no lock timeout -> 1; no SKIP LOCKED -> 1; confirm not idempotent -> 1; 55P03 not
mapped -> 1.

**Review.** Charge inside the seat transaction ("never booked without payment"), lock timeout removed: 3 of 13 fail.

**Practice.** 1: release a hold (DELETE). 2: an expired-hold sweeper that two instances run at once (SKIP LOCKED,
V3 migration). 3 (paper): optimistic holds without row locks, and a queue for a big release.
