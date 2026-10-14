# Station 026 plan: Request ids for parcel tracking

**Problem.** Dakroute support cannot find one customer's failed tracking request among 40,000 log lines a minute.
The first attempt put the caller's X-Request-Id in the MDC when present and never cleared it: the next request on that
thread, sent without an id, logged under the previous customer's id.

**Endpoint.** `GET /shipments/{awb}` 200 shipment; 400 bad AWB; 404 unknown; 503 + Retry-After when the store is
down. Every response, any path, carries X-Request-Id; every problem body carries requestId.

**Data.** No database. `RequestIdFilter` (OncePerRequestFilter, highest precedence): accept [A-Za-z0-9-]{8,64}, else
a UUID; MDC put, header set, `MDC.remove` in finally. Log pattern `%5p [rid:%X{requestId:--}]`. Micrometer counter
`tracking.lookups{outcome}`; actuator exposes health and metrics. `dakroute.tracking.simulate-outage` for drills.

**Trap.** `LeakedRequestIdTrapTest`: old filter, two requests on one thread -> B logged as A; real filter -> own id,
MDC empty after, also when the handler throws. Mutations: no remove -> 2 red; accept any id -> 2 red; no requestId in
problems -> 3 red.

**Tests.** Trap, `ShipmentContractTest`, `RequestIdLoggingTest` (captured log lines), `OperationsDrillTest` (outage:
503, ERROR line with rid, metric +1, recovery, metric endpoint).

**Practice.** 1: an access log line per request. 2: keep the id on a worker thread (TaskDecorator).
Design: tracing across services (traceparent).
