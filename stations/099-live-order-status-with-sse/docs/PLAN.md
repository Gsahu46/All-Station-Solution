# Station 099 plan: Live order status with Server-Sent Events

**Problem.** Tiffino (fictional food delivery): the app polled order status every 2 s: 30,000 requests a second at
dinner time, mostly unchanged. A first move to SSE used emitters that never time out, kept in a list nothing removed
them from: every phone that was locked left a stream behind for as long as the server ran.

**Endpoints.** `GET /orders/{id}/events` (text/event-stream, HTTP Basic, own order only else 404): `retry:` first
(it also sends the headers at once), then a "snapshot" of the current status (first visit, or a Last-Event-ID older
than the kept events) or exactly the missed events, then every change as a "status" event with a per-order id. At
DELIVERED the server ends the stream; a reconnect that has seen the last event gets 204 (the HTML standard's "stop
reconnecting"). Last-Event-ID not a number 400. `POST /orders/{id}/status` (kitchen; simulated kitchen and rider):
the next status only, else 409; unknown 404; bad value 400.

**Streams.** SseEmitter with a timeout (5 min, demo); onTimeout completes it (else Spring logs
AsyncRequestTimeoutException); onCompletion removes it from the order's list, however it ended. A heartbeat comment
every 15 s: a write to a client that has gone fails and the stream is completed with the error. Subscribe and
advance lock the order, so no change falls between the replay and joining. History of 50 events per order (demo).
Demo orders 1001-1099: odd Riya's, even Kabir's. In memory (shortcut: a broker for several servers).

**Trap.** `LeakingStreamsTrapTest`: `new SseEmitter(0L)` in a list: 20 closed clients stay 20. The API: heartbeats
drop them.

**Tests.** Real port, read line by line like EventSource. Timeout 10 s (1 s in StreamTimeoutTest), history 2,
heartbeat called by the tests.

**Review.** Timeout 0 "so phones never reconnect", no completion callback.

**Practice.** 1: rider positions as "location" events. 2: a limit of open streams per customer (429). 3 (paper):
many servers, and SSE vs polling vs WebSockets.
