# Station 102 plan: Ticket sale when the pool runs dry

**Problem.** SeatSure (fictional ticketing): when a cricket sale opened, every request waited 30 s and failed while
the database sat idle. Each order held a database connection for the whole payment call; ten slow charges took the
pool, and everyone else waited Hikari's default 30 s for a connection.

**Endpoints.** `POST /sales/{id}/orders {buyer, seats 1..6}`: 201 PAID with the charge id; 402 declined (seats back);
504 gateway too slow / 502 gateway error (seats back); 409 not enough seats; 404 no sale; 400 bad input; 503 with
Retry-After 5 when no connection is free within the pool's timeout. `GET /sales/{id}`: capacity, sold, left.

**Fix.** Three short transactions: take the seats (one conditional UPDATE) and record the order PENDING_PAYMENT;
charge with no transaction open (RestClient, connect 1 s, read 3 s, Idempotency-Key order-{id}); record PAID, or FAILED
and give the seats back. Hikari: 10 connections, connection-timeout 2000 ms (a number: these bind straight to Hikari).
Shortcut: a timed-out charge may have gone through; production asks the gateway before releasing.

**Database.** sales (sold BETWEEN 0 AND capacity, price > 0), orders (seats 1..6, amount > 0, status, PAID iff charge).

**Trap.** `PoolExhaustionTrapTest`: an old service with @Transactional around reserve + charge + record; 16 fans,
pool 4, timeout 1 s, gateway 0.7 s: some get no connection and hikaricp.connections.timeout rises. The API: all 16
paid, no pool timeouts.

**Operations.** Metrics hikaricp.connections.pending / .timeout / .usage; alerts; rollback; runbook; drills as tests
(OperationsDrillTest): a hanging gateway (504s, reads still fast, no pool timeouts) and a pool held by something else
(503 after 1 s, ERROR logged, recovers).

**Review.** @Transactional on the whole order ("no release code needed").

**Practice.** 1: a ticket.orders counter by outcome. 2: a bulkhead for gateway calls. 3 (paper): the sale at 10x.
