# Station 027 plan: Food order status flow

**Problem.** Tiffino's order status is a field set to whatever the restaurant tablet sends: orders show DELIVERED before
PREPARING, and riders pick up cancelled orders.

**Endpoints.** `GET /orders/{id}` 200 / 404. `POST /orders/{id}/status-changes` {"to"} 200 with the order and its
history; 409 a move the table forbids (currentStatus, allowedNext); 400 unknown or missing status; 404 unknown order.
Asking for the current status again is a no-op 200 (double tap).

**Data.** No database. `OrderStatus` enum with an EnumMap transition table; DELIVERED, CANCELLED, REJECTED terminal.
`Orders.move` is one `computeIfPresent`: check and write atomically. Optional for lookups. Injected Clock for history.

**Trap.** `AnyStatusTrapTest`: old setter takes DELIVERED from PLACED and PICKED_UP after CANCELLED; the real flow 409s.
Mutations: no table check -> 3 red; double tap as error -> 1 red; non-atomic get/check/put -> the race test failed in
round 0 or 1 on 3 of 3 runs.

**Tests.** Trap, `OrderStatusContractTest`, `TransitionTableTest` (all 64 pairs vs a hand-written rule, reachability,
kitchen vs customer racing 50 rounds).

**Practice.** 1: who may make which move (X-Actor, 403). 2: undo READY within 2 minutes. Design: storing the history.
