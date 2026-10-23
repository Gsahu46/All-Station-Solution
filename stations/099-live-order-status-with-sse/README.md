# Station 099 · Live order status with Server-Sent Events

Working Systems · 0–2 years · Core · Food delivery · Types: Messaging

Spring Boot 4.1.1 · Java 25 · Server-Sent Events with SseEmitter · Last-Event-ID and retry · timeouts and heartbeats · Spring Security 7 · Awaitility. Needs JDK 25 (or 21, see Set up & code). No database, no Docker. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The orders, the kitchen and the rider are simulated: demo orders 1001 to 1099 move on when the kitchen sign-in posts the next status.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **Are we there yet?**

    Tiffino's app asked for the order's status every 2 seconds. At dinner time that was 30,000 requests a second, almost all answered "same as before".

2.  **Streams that never end**

    A first move to Server-Sent Events made each stream never time out and kept it in a list. People locked their phones; the streams stayed, one for every phone that had ever opened the screen, until the server ran out.

3.  **The fix**

    Each stream has a timeout and leaves the list however it ends. A heartbeat finds phones that have gone. A reconnecting phone says which event it saw last and gets exactly what it missed.

An open connection is a resource. Every one needs an end: a timeout, a heartbeat, and a place it is removed from.

## What are we building?

A live stream of one order's status for the customer's app: the current status at once, then every change as it happens.

## An everyday analogy

A cricket commentary on the radio instead of phoning the ground every two minutes. If the signal drops, you tune back in and the commentator says what you missed since the last over you heard.

## How it works in 4 steps

1.  **Open**: the app opens `/orders/{id}/events`; the server sends the current status.
2.  **Listen**: each change arrives as an event with a number.
3.  **Reconnect**: when the stream ends (timeout, tunnel), the browser reconnects with the last number and gets only what it missed.
4.  **End**: at delivery the server ends the stream; a reconnect after that gets `204`: "stop".

Check yourself: the phone goes through a tunnel while the order goes from COOKING to OUT_FOR_DELIVERY. What does it get when it reconnects?

The browser sends `Last-Event-ID: 3` (COOKING). The server replays event 4, OUT_FOR_DELIVERY, and nothing twice. If event 4 were already too old to keep, it would get a snapshot of the current status instead.

## What this station is not

- **No WebSockets.** The app only listens; SSE is enough (Design).
- **One server.** Changes are told to this server's streams only (Production).
- **No real kitchen.** A kitchen sign-in moves the demo orders on.

## Key terms

| Term                   | Simple meaning                                                            | Everyday example                                           | In this project     |
|------------------------|---------------------------------------------------------------------------|------------------------------------------------------------|---------------------|
| **Polling**            | Asking again and again: "any news?"                                       | A child asking "are we there yet?" every minute.           | every 2 s, before   |
| **Server-Sent Events** | One long HTTP response the server keeps writing to, one event at a time.  | A radio station: you tune in once and listen.              | `text/event-stream` |
| **Event id**           | A number on each event; the browser remembers the last one.               | Page numbers in a book.                                    | `id:3`              |
| **Last-Event-ID**      | The header a reconnecting browser sends: "I had up to here".              | A bookmark.                                                | `Last-Event-ID: 3`  |
| **Timeout**            | The server ends a stream after a while; the browser reconnects by itself. | A phone call that hangs up every five minutes and redials. | 5 minutes           |
| **Heartbeat**          | A comment line sent now and then; writing to a phone that has gone fails. | "Are you still there?" on a quiet call.                    | every 15 s          |

# 2 · Build: Spec

## Business problem

**Tiffino** (a fictional food delivery company): the app polls order status every 2 seconds: 30,000 requests a second at dinner time, mostly unchanged.

## Acceptance criteria

Demo rules: streams end after 5 minutes; a heartbeat every 15 s; the last 50 events of each order are kept. Riya owns the odd orders 1001 to 1099, Kabir the even ones; password: the name plus `-demo-pass`.

1.  **Given** a customer opening their order's stream, **then** `200`, `text/event-stream`, a `retry` hint and a snapshot of the current status at once.
2.  **Given** a status change, **then** every open stream of that order gets it once, in order, with the next id.
3.  **Given** a reconnect with `Last-Event-ID`, **then** exactly the missed events; if they are no longer kept, a snapshot; if none were missed, an open stream that waits.
4.  **Given** delivery, **then** the server ends every stream; a reconnect that saw the last event gets `204`.
5.  **Given** a client that has gone, **then** its stream is dropped at the next heartbeat or timeout.
6.  **Given** someone else's or an unknown order, **then** `404`; no sign-in `401`.

## Requirements

- Every stream has a timeout and is removed from the list however it ends.
- No change can fall between a stream's replay and its joining the list.
- Statuses move one step at a time.

## Learning objectives

- Stream events with `SseEmitter`: ids, names, retry, completion.
- Resume with `Last-Event-ID` without gaps or repeats.
- Release streams with timeouts, callbacks and heartbeats.
- Test streams on a real port, as a browser reads them.
- Choose between polling, SSE and WebSockets.

# 2 · Build: API contract

## Endpoints

| Method | Path                                                | Purpose                                                         |
|--------|-----------------------------------------------------|-----------------------------------------------------------------|
| `GET`  | `/orders/{id}/events` (`Accept: text/event-stream`) | The order's live status. Optional `Last-Event-ID`.              |
| `POST` | `/orders/{id}/status`                               | Simulated kitchen and rider: move the order to its next status. |

## The stream

| Line                              | Meaning                                                                                   |
|-----------------------------------|-------------------------------------------------------------------------------------------|
| `retry:3000`                      | Wait 3 s before reconnecting. Sent first: it also gets the headers to the client at once. |
| `id:3`                            | This event's number; the browser sends the last one back as `Last-Event-ID`.              |
| `event:snapshot` / `event:status` | The current status (first visit, or after a gap), or a change.                            |
| `data:{...}`                      | The event as JSON.                                                                        |
| `:keep-alive`                     | A heartbeat comment, every 15 s; the browser ignores it.                                  |

The format is the HTML Living Standard's [server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html), which also says that a `204` tells the browser to stop reconnecting.

## Status codes

| Status | When                                                        |
|--------|-------------------------------------------------------------|
| 200    | A stream; a status change                                   |
| 204    | Reconnecting to a delivered order whose last event was seen |
| 400    | `Last-Event-ID` not a number; an unknown status             |
| 401    | No sign-in                                                  |
| 403    | The kitchen watching, or a customer changing a status       |
| 404    | No such order, or someone else's                            |
| 409    | Not the next status                                         |

## Captured examples

Captured with curl from the running app on 23 Oct 2026, in this order. A stream is read as it arrives (`curl -N`) and cut off by `docs/capture.sh` after a few seconds unless the server ends it. `Date`, connection and standard security headers are left out.

### Case 1: Riya watches order 1001 while the kitchen works

**Why:** the retry hint and a snapshot (event 1), then events 2 and 3 as cases 2 and 3 happen.

Request

``` code
GET /orders/1001/events HTTP/1.1
Authorization: Basic cml5YTpyaXlhLWRlbW8tcGFzcw==
Accept: text/event-stream
```

Response

``` code
HTTP/1.1 200 
Content-Type: text/event-stream

retry:3000

id:1
event:snapshot
data:{"id":1,"orderId":1001,"status":"PLACED","at":"2026-10-23T19:56:09.924818638Z"}

id:2
event:status
data:{"id":2,"orderId":1001,"status":"ACCEPTED","at":"2026-10-23T19:56:13.001173166Z"}

id:3
event:status
data:{"id":3,"orderId":1001,"status":"COOKING","at":"2026-10-23T19:56:13.116010561Z"}
```

### Case 2: the kitchen accepts

**Why:** event 2, sent to every open stream.

Request

``` code
POST /orders/1001/status HTTP/1.1
Authorization: Basic a2l0Y2hlbjpraXRjaGVuLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "status": "ACCEPTED"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 81

{
  "id": 2,
  "orderId": 1001,
  "status": "ACCEPTED",
  "at": "2026-10-23T19:56:13.001173166Z"
}
```

### Case 3: and starts cooking

**Why:** event 3.

Request

``` code
POST /orders/1001/status HTTP/1.1
Authorization: Basic a2l0Y2hlbjpraXRjaGVuLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "status": "COOKING"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 80

{
  "id": 3,
  "orderId": 1001,
  "status": "COOKING",
  "at": "2026-10-23T19:56:13.116010561Z"
}
```

### Case 4: out for delivery, while nobody watches

**Why:** event 4 is kept for whoever reconnects.

Request

``` code
POST /orders/1001/status HTTP/1.1
Authorization: Basic a2l0Y2hlbjpraXRjaGVuLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "status": "OUT_FOR_DELIVERY"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 89

{
  "id": 4,
  "orderId": 1001,
  "status": "OUT_FOR_DELIVERY",
  "at": "2026-10-23T19:56:15.862046314Z"
}
```

### Case 5: Riya reconnects with Last-Event-ID: 3

**Why:** event 4 replayed, nothing twice; then 5 (case 6) and the server ends the stream: curl stopped by itself.

Request

``` code
GET /orders/1001/events HTTP/1.1
Authorization: Basic cml5YTpyaXlhLWRlbW8tcGFzcw==
Accept: text/event-stream
Last-Event-ID: 3
```

Response

``` code
HTTP/1.1 200 
Content-Type: text/event-stream

retry:3000

id:4
event:status
data:{"id":4,"orderId":1001,"status":"OUT_FOR_DELIVERY","at":"2026-10-23T19:56:15.862046314Z"}

id:5
event:status
data:{"id":5,"orderId":1001,"status":"DELIVERED","at":"2026-10-23T19:56:16.959173969Z"}
```

### Case 6: delivered

**Why:** event 5, the last.

Request

``` code
POST /orders/1001/status HTTP/1.1
Authorization: Basic a2l0Y2hlbjpraXRjaGVuLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "status": "DELIVERED"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 82

{
  "id": 5,
  "orderId": 1001,
  "status": "DELIVERED",
  "at": "2026-10-23T19:56:16.959173969Z"
}
```

### Case 7: reconnecting after the end

**Why:** `204`: the browser stops.

Request

``` code
GET /orders/1001/events HTTP/1.1
Authorization: Basic cml5YTpyaXlhLWRlbW8tcGFzcw==
Accept: text/event-stream
Last-Event-ID: 5
```

Response

``` code
HTTP/1.1 204
```

### Case 8: Kabir watches Riya's order

**Why:** `404`.

Request

``` code
GET /orders/1001/events HTTP/1.1
Authorization: Basic a2FiaXI6a2FiaXItZGVtby1wYXNz
Accept: text/event-stream
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such order.",
  "instance": "/orders/1001/events",
  "status": 404,
  "title": "Not Found"
}
```

### Case 9: skipping a step

**Why:** `409`.

Request

``` code
POST /orders/1003/status HTTP/1.1
Authorization: Basic a2l0Y2hlbjpraXRjaGVuLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "status": "DELIVERED"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "An order moves one step at a time; it is PLACED.",
  "instance": "/orders/1003/status",
  "status": 409,
  "title": "Conflict"
}
```

### Case 10: no sign-in

**Why:** `401`.

Request

``` code
GET /orders/1003/events HTTP/1.1
Accept: text/event-stream
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="tiffino"
Content-Type: application/problem+json
Content-Length: 121

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid username and password.",
  "instance": "/orders/1003/events"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                          | What happens                                             | Proved by                                                  |
|-------------------------------------------------------------------------------|----------------------------------------------------------|------------------------------------------------------------|
| The old way, 20 phones that went away                                         | 20 streams kept for ever                                 | `theOldWayKeepsEveryStreamOfEveryClientThatLeft`           |
| The API, the same 20                                                          | Dropped at the next heartbeats                           | `theApiLetsGoOfClientsThatLeft`                            |
| A new watcher, then two changes                                               | Retry hint, snapshot 1, then 2 and 3                     | `aWatcherGetsTheCurrentStatusThenEachChange`               |
| Delivery; reconnects after it                                                 | Stream ended; `204`; or the missed 4 and 5, then the end | `theStreamEndsAtDeliveryAndA204TellsTheBrowserToStop`      |
| Someone else's order, unknown, no sign-in, the kitchen, a bad id; bad changes | `404`, `401`, `403`, `400`; `409`, `400`                 | `unknownOrdersSomeoneElsesAndBadRequests`                  |
| A reconnect after a missed change; one that missed nothing                    | Only the missed event; an open stream at once            | `reconnectingWithLastEventIdGetsOnlyWhatWasMissed`         |
| A Last-Event-ID older than the kept events                                    | A snapshot instead of a gap                              | `aLastEventIdOlderThanTheKeptEventsGetsASnapshotInstead`   |
| 30 watchers, four changes                                                     | Each gets 1 to 5 once, in order, then the end            | `everyWatcherGetsEveryChangeOnceAndInOrder`                |
| A stream that times out                                                       | Ended by the server; the reconnect misses nothing        | `aStreamTimesOutAndTheClientResumesWithoutMissingAnything` |
| After the timeout                                                             | Not held any more                                        | `aStreamThatTimedOutIsNoLongerHeld`                        |

## The trap

Plausible but wrong

Never timing out emitters, leaking connections and threads.

- **The old way.** `new SseEmitter(0L)` (no timeout) kept in a list. Twenty phones open the stream and go away; four seconds later the list still holds all twenty, and nothing will ever end them. With a sending thread per stream, as many first versions have, those threads stay too.
- **The API.** The same twenty: the next heartbeats write to them, the writes fail, and each stream ends and leaves the list.

While building, each part was undone once: no timeout turned 2 tests red; no completion callback 2; no replay 2; no gap check 1; no `204` 1; streams not ended at delivery 2; any customer's order 1; no retry hint 1; skipping a status 1; the retry hint not sent first 1 (a reconnect that had missed nothing got no answer at all). Two things turned nothing red and were simplified: removing a stream in the timeout handler and in the heartbeat's failure path (the completion callback already does it). Removing the order's lock turned nothing red either: no test reaches the instant between a replay and joining the list. The lock stays; that case is not proven by a test.

``` code
package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/** Twenty phones open the order screen, then the users lock them. Written first. */
@Import(LeakingStreamsTrapTest.OldWay.class)
class LeakingStreamsTrapTest extends ApiTest {

    /** The old way: an emitter that never times out, kept in a list that nothing ever removes from. */
    @TestConfiguration
    static class OldWay {
        static final List<SseEmitter> STREAMS = new CopyOnWriteArrayList<>();

        @RestController   // a member of this configuration: registered with it
        static class OldStream {
            @GetMapping("/old/orders/1001/events")
            SseEmitter events() throws java.io.IOException {
                SseEmitter emitter = new SseEmitter(0L);   // 0: no timeout
                emitter.send("PLACED");
                STREAMS.add(emitter);
                return emitter;
            }
        }

        @Bean
        @Order(0)
        SecurityFilterChain oldWayIsOpen(HttpSecurity http) throws Exception {
            return http.securityMatcher("/old/**").authorizeHttpRequests(a -> a.anyRequest().permitAll()).build();
        }
    }

    @Test
    void theOldWayKeepsEveryStreamOfEveryClientThatLeft() throws Exception {
        List<AutoCloseable> phones = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            var response = HTTP.send(HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/old/orders/1001/events")).build(),
                    HttpResponse.BodyHandlers.ofInputStream());
            phones.add(response.body());
        }
        for (AutoCloseable phone : phones) {
            phone.close();   // locked: the connection is gone from the phone's side
        }
        // Nothing ever ends these streams or removes them: twenty dead clients, held for as long as the server runs.
        await().during(Duration.ofSeconds(4)).atMost(Duration.ofSeconds(5)).until(() -> OldWay.STREAMS.size() == 20);
    }

    @Test
    void theApiLetsGoOfClientsThatLeft() throws Exception {
        int before = streams.streams();
        List<Stream> phones = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            phones.add(open("riya", 1001, null));
        }
        phones.forEach(p -> p.awaitEvents(1));
        assertThat(streams.streams()).isEqualTo(before + 20);
        for (Stream phone : phones) {
            phone.close();
        }
        // The next heartbeats write to them, the writes fail, and they are dropped. (Every 15 s in production.)
        await().atMost(Duration.ofSeconds(5)).until(() -> {
            streams.heartbeat();
            return streams.streams() == before;
        });
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 10 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Watch in one terminal, cook in another:

``` code
curl -N -u riya:riya-demo-pass http://localhost:8080/orders/1021/events
curl -u kitchen:kitchen-demo-pass -H 'Content-Type: application/json' -d '{"status":"ACCEPTED"}' http://localhost:8080/orders/1021/status
```

Stop the first command, move the order on, and reconnect with `-H 'Last-Event-ID: 2'`: only what you missed arrives.

## Troubleshooting

| You see                                        | Cause                                        | Fix                                                               |
|------------------------------------------------|----------------------------------------------|-------------------------------------------------------------------|
| Events arrive in bursts, late                  | A proxy buffers the response.                | Turn buffering off for the path (nginx: `X-Accel-Buffering: no`). |
| The stream ends every 60 s                     | A proxy's idle timeout.                      | Heartbeats more often than it; the browser reconnects anyway.     |
| The browser reconnects for ever after delivery | The server answers 200 with an empty stream. | Answer `204`.                                                     |

## Project layout

``` tree
stations/099-live-order-status-with-sse/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tiffino/orders/
│   ├── OrderController.java   ├── OrderStreams.java   ├── SecurityConfig.java
│   └── ProblemResponses.java   └── OrdersApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/tiffino/orders/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tiffino/orders/OrderController.java`

Does  
The two endpoints.

Why  
The customer's own order or `404`; `204` when there is nothing left to stream; one step at a time for the kitchen.

Without it  
Watching someone else's order; statuses out of order.

#### `src/main/java/com/tiffino/orders/OrderStreams.java`

Does  
Orders, their events and their streams.

Why  
Replay or snapshot on subscribe, then the stream joins the order's list; every change goes to every stream; heartbeats; the end at delivery.

Without it  
Streams that outlive their clients; events lost or repeated on reconnect.

- Subscribe and advance lock the order, so no change falls between a stream's replay and its joining the list.
- `onCompletion` removes a stream however it ended: delivered, timed out, or a failed write (`completeWithError`).
- `onTimeout` only completes the stream: without it Spring logs an `AsyncRequestTimeoutException` for every stream that times out.
- `retry` is sent first because it also flushes the headers: a reconnect that missed nothing would otherwise wait with no answer at all until the next event. Found while building.
- Shortcut: sends run on the kitchen's request thread; a slow reader slows it down.

#### `src/main/java/com/tiffino/orders/SecurityConfig.java`

HTTP Basic: customers watch, the kitchen changes statuses.

#### `src/main/java/com/tiffino/orders/ProblemResponses.java`

`401` and `403` in the problem shape.

#### `src/main/resources/application.yaml`

Timeout, retry, heartbeat and history: the demo rules.

#### `src/main/java/com/tiffino/orders/OrdersApplication.java`

Entry point; scheduling on, for the heartbeat.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                               | Test class                                            | Result |
|---------------|-------------------------------------------|-------------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found  | `OrderEventsContractTest` (3)                         | pass   |
| Every station | Reproduce the failure before the fix      | `LeakingStreamsTrapTest` (2)                          | pass   |
| Messaging     | Duplicate delivery, retry and dead letter | `ReconnectMessagingTest` (3), `StreamTimeoutTest` (2) | pass   |

For a stream, "duplicate delivery" is a reconnect that gets events twice (it does not: only what is after `Last-Event-ID`); "retry" is the browser reconnecting after a timeout without missing anything; the "dead letter" cases are events no longer kept, replaced by a snapshot, and clients that have gone, dropped rather than written to again and again.

The tests use a real port and read each stream line by line, as a browser's EventSource does. Streams end after 10 s here (1 s in `StreamTimeoutTest`), two events are kept per order, and the tests call the heartbeat themselves.

Found while building: 30 watchers opened one after another took longer than a short stream timeout, because each sign-in checks a BCrypt password; they are opened at once now. And a test that opened an old-way stream waited for ever: an emitter that has sent nothing has not sent its headers either.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.ReconnectMessagingTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.OrderEventsContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.StreamTimeoutTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.LeakingStreamsTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tiffino/orders/LeakingStreamsTrapTest.java`

Written first: streams that never end, against the API's.

#### `src/test/java/com/tiffino/orders/OrderEventsContractTest.java`

Snapshot and changes; the end and the 204; bad and foreign requests.

#### `src/test/java/com/tiffino/orders/ReconnectMessagingTest.java`

Reconnects with Last-Event-ID; a gap; 30 watchers.

#### `src/test/java/com/tiffino/orders/StreamTimeoutTest.java`

Streams that time out after 1 s.

#### `src/test/java/com/tiffino/orders/ApiTest.java`

Shared setup: a stream reader, the kitchen helper, the test settings.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tiffino/orders/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RiderLocationChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 13 tests pass (10 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 30 minutes

## Where is the rider?

While an order is out for delivery, `POST /orders/{id}/location {"lat": ..., "lng": ...}` sends the rider's position. Watchers get an event named `location`, numbered in the same sequence, so a reconnect replays it. Before or after the ride: `409`; a latitude over 90: `400`.

**Done when:** both tests in `RiderLocationChallengeTest` pass.

Hints

- Give the event an optional position; name it by whether it has one.
- `@DecimalMin` and `@DecimalMax` on the request's numbers.

#### `challenge/RiderLocationChallengeTest.java`

``` code
package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: while an order is out for delivery, the rider's phone sends its position:
 * POST /orders/{id}/location {"lat": 12.97, "lng": 77.59} (the kitchen sign-in stands in for the rider). Watchers get
 * an event named "location", numbered like every other event, so a reconnect replays it too. Before or after the
 * ride: 409.
 */
class RiderLocationChallengeTest extends ApiTest {

    int location(long orderId, String json) throws Exception {
        return HTTP.send(HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/orders/" + orderId + "/location"))
                .header("Authorization", basic("kitchen")).header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json)).build(), HttpResponse.BodyHandlers.discarding()).statusCode();
    }

    @Test
    void watchersSeeTheRiderMove() throws Exception {
        assertThat(location(1051, "{\"lat\":12.97,\"lng\":77.59}")).isEqualTo(409);   // not out for delivery yet
        for (String status : new String[]{"ACCEPTED", "COOKING", "OUT_FOR_DELIVERY"}) {
            assertThat(advance(1051, status)).isEqualTo(200);
        }
        try (Stream riya = open("riya", 1051, 4L)) {
            assertThat(location(1051, "{\"lat\":12.9716,\"lng\":77.5946}")).isEqualTo(200);
            var events = riya.awaitEvents(1);
            assertThat(events.getFirst().event()).isEqualTo("location");
            assertThat(events.getFirst().id()).isEqualTo("5");
            assertThat(events.getFirst().data()).contains("\"lat\":12.9716", "\"lng\":77.5946");
        }
        try (Stream later = open("riya", 1051, 4L)) {   // a reconnect replays the location like any event
            assertThat(later.awaitEvents(1).getFirst().event()).isEqualTo("location");
        }
    }

    @Test
    void badPositionsAre400() throws Exception {
        assertThat(location(1053, "{\"lat\":91,\"lng\":77.59}")).isEqualTo(400);
        assertThat(location(1053, "{\"lat\":12.97}")).isEqualTo(400);
        assertThat(location(9999, "{\"lat\":12.97,\"lng\":77.59}")).isEqualTo(404);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## A limit on open streams

A customer may hold a limited number of open streams (`tiffino.sse.max-streams-per-customer`, 50 by default, 3 in the test). An app stuck in a reconnect loop gets `429` with `Retry-After`; when one of its streams ends, it may open another.

**Done when:** the test in `StreamLimitChallengeTest` passes.

Hints

- Count when a stream joins a list, and uncount in the same completion callback that removes it.
- Check and count under one lock, or two requests could both take the last place.

#### `challenge/StreamLimitChallengeTest.java`

``` code
package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/**
 * Challenge 2: a limit on open streams per customer, tiffino.sse.max-streams-per-customer (a demo rule: 50 by
 * default, 3 in this test). An app stuck in a reconnect loop gets 429 with Retry-After instead of opening hundreds;
 * when one of its streams ends, it may open another.
 */
@org.springframework.test.context.TestPropertySource(properties = "tiffino.sse.max-streams-per-customer=3")
class StreamLimitChallengeTest extends ApiTest {

    @Test
    void theFourthOpenStreamIs429() throws Exception {
        List<Stream> open = new ArrayList<>();
        for (int i = 0; i < 3; i++) {
            open.add(open("kabir", 1062, null));
        }
        open.forEach(s -> s.awaitEvents(1));
        try (Stream fourth = open("kabir", 1064, null)) {
            assertThat(fourth.status).isEqualTo(429);
        }
        try (Stream riya = open("riya", 1061, null)) {
            assertThat(riya.status).isEqualTo(200);   // another customer is not affected
        }
        open.getFirst().close();   // one phone goes away; the next heartbeat notices
        await().atMost(Duration.ofSeconds(5)).until(() -> {
            streams.heartbeat();
            try (Stream again = open("kabir", 1062, null)) {
                return again.status == 200;
            }
        });
        for (Stream s : open) {
            s.close();
        }
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Ten servers, one kitchen

Tiffino runs ten servers; a phone's stream is on one of them, and the kitchen's update reaches another. Design how every server learns about the change (Valkey pub/sub, Kafka, or a database's LISTEN/NOTIFY), where the event history lives so any server can replay it, and how many streams one server can hold. Then argue: would WebSockets or plain polling with `ETag`s be better for this screen?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: streams that never end, and clients that leave.
2.  Number every event per order and keep the last few.
3.  Subscribe: retry hint, replay or snapshot, then join the list, all under the order's lock.
4.  End streams: timeout, completion callback, heartbeat, delivery and `204`.

## Design alternatives and trade-offs

| Approach                                  | What it costs                                                  | Verdict                     |
|-------------------------------------------|----------------------------------------------------------------|-----------------------------|
| SSE with ids, timeouts and heartbeats     | An open connection per watcher; one-way only.                  | Chosen                      |
| Polling every 2 s                         | 30,000 requests a second, nearly all "no change".              | The problem                 |
| SSE that never times out                  | Connections and memory held for every client that ever left.   | The trap                    |
| Polling with `ETag` and a longer interval | Cheaper per request, still late and still many.                | Fine for slow-changing data |
| WebSockets                                | Two-way; more to run (upgrades, proxies, own reconnect logic). | When the client also talks  |

## Database design

No database: orders and their last events are in memory. With several servers, the history moves to a shared store and changes go through a broker (challenge 3).

# 3 · Go deeper: Production

Connections  
Each watcher holds a connection (not a thread: servlet async releases it). Size the server's connection limit and file descriptors for the busiest hour.

Proxies  
Turn response buffering off for the stream's path and keep heartbeats shorter than every idle timeout on the way.

HTTP/1.1  
Browsers allow about six connections per host over HTTP/1.1; streams count. HTTP/2 removes that limit.

Several servers  
Publish changes through a broker so every server can tell its own watchers; keep the history somewhere shared.

Slow readers  
Sends here run on the caller's thread; with many watchers, hand them to an executor with a bounded queue and drop readers that fall behind.

# 3 · Go deeper: Interview

## Interview takeaways

When do you choose SSE over polling and WebSockets?

SSE when the server pushes and the client only listens: one HTTP response, automatic reconnects, event ids. Polling for rare changes; WebSockets when the client talks back too.

How does a client resume after a dropped connection?

The browser reconnects after the retry delay and sends Last-Event-ID; the server replays what came after it.

How do you stop leaking SSE connections?

A timeout on every emitter, removal in a completion callback, and heartbeats that make writes to gone clients fail.

How does the server tell the browser to stop reconnecting?

Answer 204 No Content.

What if the client's last event is no longer kept?

Send a snapshot of the current state instead of pretending nothing was missed.

How do you test SSE?

On a real port, reading the stream line by line, with Awaitility for each expected event.

## Self-check rubric

| Area        | Meets the bar         | Above the bar                                                                   |
|-------------|-----------------------|---------------------------------------------------------------------------------|
| Correctness | All 10 tests pass.    | You ran the flawed version and explained each failure.                          |
| Streams     | Events reach the app. | Ids, retry, snapshot, 204 at the end.                                           |
| Resources   | A timeout.            | Removal however a stream ends, and heartbeats; you can say what a stream costs. |
| Testing     | One stream test.      | Reconnects, gaps, timeouts and many watchers on a real port.                    |

# 3 · Go deeper: Review

## The pull request

A teammate "simplifies the streams": no timeout, "so phones never have to reconnect", and no completion callback, "since streams leave the list when a write to them fails". Read the file and list every problem before opening the findings.

#### `review/OrderStreams.java`

``` code
package com.tiffino.orders;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;
import java.util.stream.LongStream;

/**
 * Each order's status, its recent events, and the streams listening to it.
 * shortcut: in this server's memory; with several servers, publish status changes through a broker (Valkey pub/sub,
 * Kafka) so every server can tell its own subscribers.
 */
@Service
class OrderStreams {

    enum Status {
        PLACED, ACCEPTED, COOKING, OUT_FOR_DELIVERY, DELIVERED;

        Optional<Status> next() {
            return ordinal() + 1 < values().length ? Optional.of(values()[ordinal() + 1]) : Optional.empty();
        }
    }

    record Event(long id, long orderId, Status status, Instant at) {
    }

    static final class Order {
        final long id;
        final String customer;
        Status status = Status.PLACED;
        long lastEventId;
        final Deque<Event> history = new ArrayDeque<>();
        final List<SseEmitter> streams = new CopyOnWriteArrayList<>();

        Order(long id, String customer) {
            this.id = id;
            this.customer = customer;
            history.add(new Event(++lastEventId, id, status, Instant.now()));
        }
    }

    /** Demo orders 1001 to 1099: odd ones are Riya's, even ones Kabir's. */
    private final Map<Long, Order> orders = LongStream.rangeClosed(1001, 1099).boxed()
            .collect(Collectors.toUnmodifiableMap(id -> id, id -> new Order(id, id % 2 == 1 ? "riya" : "kabir")));
    private final Duration timeout;
    private final Duration retry;
    private final int historySize;

    OrderStreams(@Value("${tiffino.sse.timeout}") Duration timeout, @Value("${tiffino.sse.retry}") Duration retry,
                 @Value("${tiffino.sse.history}") int historySize) {
        this.timeout = timeout;
        this.retry = retry;
        this.historySize = historySize;
    }

    Optional<Order> order(long id, String customer) {
        return Optional.ofNullable(orders.get(id)).filter(o -> o.customer.equals(customer));
    }

    Optional<Order> order(long id) {
        return Optional.ofNullable(orders.get(id));
    }

    /**
     * A stream for one order: what the client missed (or the current status), then every change. Empty when the
     * order is delivered and the client has seen that: the controller answers 204, which tells the browser to stop.
     */
    Optional<SseEmitter> subscribe(Order order, Long lastEventId) {
        synchronized (order) {   // nothing can change between the replay and joining the list
            if (order.status == Status.DELIVERED && lastEventId != null && lastEventId >= order.lastEventId) {
                return Optional.empty();
            }
            SseEmitter emitter = new SseEmitter(0L);   // no timeout: phones never have to reconnect
            List<Event> missed = lastEventId == null ? null
                    : order.history.stream().filter(e -> e.id() > lastEventId).toList();
            boolean gap = missed != null && !missed.isEmpty() && missed.getFirst().id() != lastEventId + 1;
            try {
                // The reconnect delay first, always: it also sends the headers at once, even when nothing was missed.
                emitter.send(SseEmitter.event().reconnectTime(retry.toMillis()));
                if (missed == null || gap) {
                    // First visit, or events we no longer keep: the current status instead of a hole in the story.
                    emitter.send(SseEmitter.event().id(Long.toString(order.lastEventId)).name("snapshot")
                            .data(order.history.getLast(), MediaType.APPLICATION_JSON));
                } else {
                    for (Event e : missed) {
                        emitter.send(event(e));
                    }
                }
            } catch (IOException e) {
                emitter.completeWithError(e);
                return Optional.of(emitter);
            }
            if (order.status == Status.DELIVERED) {
                emitter.complete();   // the story is over: no need to stay connected
                return Optional.of(emitter);
            }
            order.streams.add(emitter);   // streams leave the list when a write to them fails
            return Optional.of(emitter);
        }
    }

    /** The kitchen or the rider moves the order on, one step at a time. Empty if that is not the next step. */
    Optional<Event> advance(Order order, Status to) {
        synchronized (order) {
            if (order.status.next().filter(to::equals).isEmpty()) {
                return Optional.empty();
            }
            order.status = to;
            Event event = new Event(++order.lastEventId, order.id, to, Instant.now());
            order.history.add(event);
            while (order.history.size() > historySize) {
                order.history.removeFirst();
            }
            // shortcut: sends happen on this request's thread, one stream after another; a client that reads slowly
            // makes the kitchen wait. Hand the sends to an executor when an order has many watchers.
            for (SseEmitter stream : order.streams) {
                try {
                    stream.send(event(event));
                    if (to == Status.DELIVERED) {
                        stream.complete();
                    }
                } catch (IOException | IllegalStateException gone) {
                    drop(stream, gone);
                }
            }
            return Optional.of(event);
        }
    }

    /** A comment line to every stream. A client that has gone makes the write fail; its stream is dropped, not retried. */
    @Scheduled(fixedRateString = "${tiffino.sse.heartbeat}")
    void heartbeat() {
        for (Order order : orders.values()) {
            for (SseEmitter stream : order.streams) {
                try {
                    stream.send(SseEmitter.event().comment("keep-alive"));
                } catch (IOException | IllegalStateException gone) {
                    drop(stream, gone);
                }
            }
        }
    }

    int streams() {
        return orders.values().stream().mapToInt(o -> o.streams.size()).sum();
    }

    /** Ends a stream whose client has gone; its completion callback takes it off the list. */
    private static void drop(SseEmitter stream, Exception why) {
        stream.completeWithError(why);
    }

    private static SseEmitter.SseEventBuilder event(Event e) {
        return SseEmitter.event().id(Long.toString(e.id())).name("status").data(e, MediaType.APPLICATION_JSON);
    }
}
```

## Findings

1No timeout

"So phones never have to reconnect": and a phone that leaves without a word is never noticed unless something writes to it. Reconnects are cheap and built into the browser; a stream with no end is a connection held for ever.

**Test evidence:** `aStreamTimesOutAndTheClientResumesWithoutMissingAnything` and `aStreamThatTimedOutIsNoLongerHeld` fail.

2Streams leave the list only on a failed write

"Streams leave the list when a write to them fails": but in this version nothing removes them, even then. A failed heartbeat ends the stream, and the ended stream stays in the list for ever; delivered orders' streams too.

**Test evidence:** `theApiLetsGoOfClientsThatLeft` fails: the twenty streams stay.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                | Fixed version | Flawed version |
|---------------------------|---------------|----------------|
| `OrderEventsContractTest` | 3 / 3         | 3 / 3          |
| `ReconnectMessagingTest`  | 3 / 3         | 3 / 3          |
| `LeakingStreamsTrapTest`  | 2 / 2         | 1 / 2          |
| `StreamTimeoutTest`       | 2 / 2         | 0 / 2          |

Every event still reaches every phone that is watching. The flaw is in the phones that stopped watching: invisible in a demo, a slow leak at dinner time.
