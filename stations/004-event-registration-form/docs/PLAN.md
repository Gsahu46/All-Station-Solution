# Station 004 plan: Event registration form

**Problem.** SeatSure saves whatever the client sends: blank names, "asha" as email, 0 tickets.

**Endpoints.** `POST /events/{eventId}/registrations` → 201 + Location, 400 (errors map), 404 unknown event, 415 not JSON.
`GET /events/{eventId}/registrations/{id}` → 200, 404 (also for another event's id), 400 malformed UUID.

**Data.** No database. Two events; registrations in a ConcurrentHashMap. Server sets id, eventId, registeredAt.

**Trap.** No @Valid. `TrustingTheClientTrapTest`: naive saves garbage; fixed answers 400 with three messages, saves nothing.
Mutation: removing @Valid -> 4 tests red. Found while building: 2.5 tickets saved as 2 (Jackson ACCEPT_FLOAT_AS_INT);
fixed with accept-float-as-int: false; the test was red before and green after.

**Tests.** `TrustingTheClientTrapTest`, `RegistrationContractTest`, `RegistrationRequestTest` (plain Validator).

**Practice.** 1: one registration per email per event, 409, putIfAbsent. 2: CSV export with RFC 4180 quoting and
formula-injection guard. Design: seat limits (pointer to station 082).
