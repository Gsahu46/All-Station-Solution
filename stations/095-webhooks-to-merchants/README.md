# Station 095 · Webhooks to merchants

Working Systems · 0–2 years · Core · Payments · Types: Database, Security, Messaging, Idempotency

Spring Boot 4.1.1 · Java 25 · @Scheduled · transactional outbox · HMAC-SHA256 (Standard Webhooks format) · exponential backoff · FOR UPDATE SKIP LOCKED · java.net.http · Spring Security 7 · PostgreSQL 17 · Testcontainers · Awaitility. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Payments are simulated: a test event records that a payment was captured; no payment exists and no money moves. The merchants and their servers are demo ones (a Python script in the captures, small Java servers in the tests).

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 17 tests.

# 1 · Understand

## The problem in real life

1.  **Down for five minutes**

    Ravi's shop server restarts for an update. In those five minutes three customers pay. Paysetu posts each "payment captured" once, gets a 503, and moves on.

2.  **Orders that never ship**

    Ravi's system never hears about the three payments, so the orders stay unpaid. The customers call; Ravi calls Paysetu. And because nothing was signed, a fake "paid" sent by anyone would have shipped goods for free.

3.  **The fix**

    Each payment is written with a delivery for each of Ravi's servers, in one transaction. A dispatcher sends them signed, waits longer after each failure, logs every try, and after eight failures keeps the delivery as failed for a person to see.

A notification you send once is a notification you lose. Write it down first, sign it, retry it, and keep the record.

## What are we building?

Merchants register a URL and get a secret. Every captured payment is delivered to each URL, signed, retried with growing waits, and listed in a delivery log the merchant can read.

## An everyday analogy

A courier service: each parcel is booked before it leaves, sealed, tried again tomorrow and the day after when nobody is home, and after the last try it waits at the depot. The tracking page shows every doorstep visit.

## How it works in 4 steps

1.  **Register**: the merchant gives a URL and gets a signing secret, shown once.
2.  **Record**: a captured payment writes an event and one delivery per URL in one transaction.
3.  **Send**: every second a dispatcher takes what is due, signs it and posts it. 2xx means delivered.
4.  **Retry or stop**: after a failure it waits 30 s, then twice as long each time; the 8th failure is final.

Check yourself: the merchant's server took the request, saved the payment, then crashed before answering. What happens?

We see no 2xx, so we retry, and the merchant gets the same payment twice. That is why every retry carries the same `webhook-id`: the merchant drops repeats by it. Webhooks are delivered at least once, not exactly once.

## What this station is not

- **No real payments.** A test event stands in for a captured payment.
- **No checks of where a URL points.** A merchant could register an internal address; see Production.
- **No ordering.** A retry can arrive after a newer event.

## Key terms

| Term                    | Simple meaning                                                                     | Everyday example                                           | In this project             |
|-------------------------|------------------------------------------------------------------------------------|------------------------------------------------------------|-----------------------------|
| **Webhook**             | An HTTP request we send to the merchant's server when something happens.           | A courier ringing your bell instead of you phoning to ask. | `payment.captured`          |
| **Outbox**              | A table of messages still to send, written together with the change they announce. | Letters in the out tray, written while the deal is signed. | `deliveries`                |
| **Signature**           | A code only someone with the shared secret can make, sent with the request.        | A seal on an envelope.                                     | `webhook-signature: v1,...` |
| **HMAC-SHA256**         | The way the signature is made: a hash of the message mixed with the secret.        | A seal stamped with a ring only two people own.            | `WebhookSignature.sign`     |
| **Exponential backoff** | Waiting longer after each failure: 30 s, 1 min, 2 min, ...                         | Calling a busy shop again later, and later still.          | `Dispatcher.backoff`        |
| **Dead letter**         | A message we stop trying, kept for a person to look at.                            | A parcel back at the depot after eight failed doorsteps.   | `status FAILED`             |

# 2 · Build: Spec

## Business problem

**Paysetu** (a fictional payments company): merchants miss payment notifications when their server is down for five minutes, and cannot tell a real notification from a forged one.

## Acceptance criteria

Demo users: ravi (merchant 1) and meena (merchant 2); password: the name plus `-demo-pass`. Demo rules: first retry after 30 s, doubled each time, 8 attempts (about an hour); 5 s per attempt; signatures older than 5 minutes refused.

1.  **Given** a valid URL, **then** `201` with a `whsec_` secret, shown only here; the same URL again `409`.
2.  **Given** a captured payment, **then** `202` and, within a second, a POST to each URL with `webhook-id`, `webhook-timestamp` and a valid `webhook-signature`.
3.  **Given** the merchant down for five minutes, **then** the payment arrives on the first try after it is back (7.5 minutes in), with the same id.
4.  **Given** eight failures, **then** the delivery is `FAILED` and not tried again; the log shows all eight.
5.  **Given** the same payment reported twice, **then** one event and one delivery per URL; with another amount `409`.
6.  **Given** another merchant's id or delivery, **then** `403` or `404`; no sign-in `401`.

## Requirements

- Nothing is sent inside the request that records the payment.
- Two servers running the dispatcher never send the same delivery at the same time.
- The attempt limit, the states and the one-delivery-per-endpoint rule are also database constraints.

## Learning objectives

- Write an event and its deliveries atomically (a transactional outbox) and send them from a `@Scheduled` job.
- Sign requests with HMAC-SHA256 and verify them in constant time with a timestamp tolerance.
- Retry with exponential backoff and stop with a dead letter.
- Claim work from a table safely with `FOR UPDATE SKIP LOCKED` and a lease.
- Test time-based behaviour with a clock you move, not with sleeps.

# 2 · Build: API contract

## Endpoints

| Method | Path                                                  | Purpose                                                                          |
|--------|-------------------------------------------------------|----------------------------------------------------------------------------------|
| `POST` | `/merchants/{id}/webhook-endpoints`                   | Register a URL; the answer has the signing secret.                               |
| `POST` | `/merchants/{id}/test-events`                         | Demo helper: record a captured payment (like a dashboard's "send test webhook"). |
| `GET`  | `/webhook-deliveries?status=PENDING|DELIVERED|FAILED` | The merchant's deliveries, newest first (at most 100).                           |
| `GET`  | `/webhook-deliveries/{id}`                            | One delivery and every attempt.                                                  |

## What the merchant receives

| Header              | Value                                                                    |
|---------------------|--------------------------------------------------------------------------|
| `webhook-id`        | The event id: the same on every retry, so the merchant can drop repeats. |
| `webhook-timestamp` | Seconds since 1970 when this attempt was signed.                         |
| `webhook-signature` | `v1,` + Base64 of HMAC-SHA256(secret, `id.timestamp.body`).              |

The format of [Standard Webhooks](https://www.standardwebhooks.com/), a community specification (not an IETF or W3C standard).

## Status codes

| Status | When                                                                                                      |
|--------|-----------------------------------------------------------------------------------------------------------|
| 201    | Endpoint registered                                                                                       |
| 202    | Payment recorded; deliveries will be sent                                                                 |
| 200    | The same payment again (the first event), or a read                                                       |
| 400    | Not an http(s) URL with a host; a user name or \#fragment; a bad payment ref or amount; an unknown status |
| 401    | No sign-in, or a wrong password                                                                           |
| 403    | Another merchant's id in the path                                                                         |
| 404    | No such delivery, or another merchant's                                                                   |
| 409    | The URL is already registered; the payment was reported with another amount                               |

## Captured examples

Captured with curl from the running app on 23 Oct 2026, in this order. Ravi's first server is `docs/test-merchant.py`, a Python script that checks every signature itself and answers 503 to its first request; nothing listens at his second URL. `Date`, connection and standard security headers are left out.

### Case 1: Ravi registers his server

**Why:** `201`; the secret is shown this once.

Request

``` code
POST /merchants/1/webhook-endpoints HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "url": "http://127.0.0.1:9095/hooks/paysetu"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "id": 1,
  "url": "http://127.0.0.1:9095/hooks/paysetu",
  "secret": "whsec_7/d/nd1LxEMb/WghXzZW7/dHbgNcCY7H",
  "createdAt": "2026-10-23T16:21:13.734266Z"
}
```

### Case 2: a second URL

**Why:** nothing listens there: its delivery will fail.

Request

``` code
POST /merchants/1/webhook-endpoints HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "url": "http://127.0.0.1:9096/hooks"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "id": 2,
  "url": "http://127.0.0.1:9096/hooks",
  "secret": "whsec_kNEOjDAWvQXJQdWEpeb1dVzEUMbajSOg",
  "createdAt": "2026-10-23T16:21:13.868084Z"
}
```

### Case 3: the same URL again

**Why:** `409` (`endpoints_url_once_per_merchant`).

Request

``` code
POST /merchants/1/webhook-endpoints HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "url": "http://127.0.0.1:9095/hooks/paysetu"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "This URL is already registered for this merchant.",
  "instance": "/merchants/1/webhook-endpoints",
  "status": 409,
  "title": "Conflict"
}
```

### Case 4: a file path

**Why:** `400`.

Request

``` code
POST /merchants/1/webhook-endpoints HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "url": "file:///etc/passwd"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "The URL must be http or https, with a host and without a user name or #fragment.",
  "instance": "/merchants/1/webhook-endpoints",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: a payment is captured

**Why:** `202`: one delivery per URL, sent by the dispatcher, not by this request.

Request

``` code
POST /merchants/1/test-events HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "paymentRef": "PAY-1001",
  "amountPaise": 49900
}
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json

{
  "eventId": "b8a6a692-952e-4abf-b6ac-717709d1e081",
  "paymentRef": "PAY-1001",
  "deliveries": 2,
  "replay": false
}
```

### Case 6: the same payment again

**Why:** `200`, the same event: nothing new is sent.

Request

``` code
POST /merchants/1/test-events HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "paymentRef": "PAY-1001",
  "amountPaise": 49900
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "eventId": "b8a6a692-952e-4abf-b6ac-717709d1e081",
  "paymentRef": "PAY-1001",
  "deliveries": 2,
  "replay": true
}
```

### Case 7: the same payment, another amount

**Why:** `409`: that is a bug in the caller, not a repeat.

Request

``` code
POST /merchants/1/test-events HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "paymentRef": "PAY-1001",
  "amountPaise": 4990000
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "PAY-1001 was already reported with a different amount.",
  "instance": "/merchants/1/test-events",
  "status": 409,
  "title": "Conflict"
}
```

### Case 8: Meena points Ravi's payments at her URL

**Why:** `403`.

Request

``` code
POST /merchants/1/webhook-endpoints HTTP/1.1
Authorization: Basic bWVlbmE6bWVlbmEtZGVtby1wYXNz
Content-Type: application/json

{
  "url": "http://127.0.0.1:9097/steal"
}
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json

{
  "detail": "You can only manage your own merchant's webhooks.",
  "instance": "/merchants/1/webhook-endpoints",
  "status": 403,
  "title": "Forbidden"
}
```

### Case 9: no sign-in

**Why:** `401`.

Request

``` code
GET /webhook-deliveries HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="paysetu"
Content-Type: application/problem+json
Content-Length: 121

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid username and password.",
  "instance": "/webhook-deliveries"
}
```

### Case 10: the log 3 s later

**Why:** both deliveries tried once: 503 and no connection; the next tries are 30 s after the first.

Request

``` code
GET /webhook-deliveries HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 605

[
  {
    "id": 2,
    "eventId": "b8a6a692-952e-4abf-b6ac-717709d1e081",
    "type": "payment.captured",
    "paymentRef": "PAY-1001",
    "endpointUrl": "http://127.0.0.1:9096/hooks",
    "status": "PENDING",
    "attempts": 1,
    "lastStatusCode": null,
    "lastError": "could not connect",
    "nextAttemptAt": "2026-10-23T16:21:44.503267Z",
    "deliveredAt": null
  },
  {
    "id": 1,
    "eventId": "b8a6a692-952e-4abf-b6ac-717709d1e081",
    "type": "payment.captured",
    "paymentRef": "PAY-1001",
    "endpointUrl": "http://127.0.0.1:9095/hooks/paysetu",
    "status": "PENDING",
    "attempts": 1,
    "lastStatusCode": 503,
    "lastError": "HTTP 503",
    "nextAttemptAt": "2026-10-23T16:21:44.503264Z",
    "deliveredAt": null
  }
]
```

### Case 11: about 30 s later

**Why:** the retry was answered 200.

Request

``` code
GET /webhook-deliveries?status=DELIVERED HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 297

[
  {
    "id": 1,
    "eventId": "b8a6a692-952e-4abf-b6ac-717709d1e081",
    "type": "payment.captured",
    "paymentRef": "PAY-1001",
    "endpointUrl": "http://127.0.0.1:9095/hooks/paysetu",
    "status": "DELIVERED",
    "attempts": 2,
    "lastStatusCode": 200,
    "lastError": null,
    "nextAttemptAt": null,
    "deliveredAt": "2026-10-23T16:21:44.74506Z"
  }
]
```

### Case 12: one delivery and its attempts

**Why:** what a merchant's support team reads.

Request

``` code
GET /webhook-deliveries/1 HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 509

{
  "delivery": {
    "id": 1,
    "eventId": "b8a6a692-952e-4abf-b6ac-717709d1e081",
    "type": "payment.captured",
    "paymentRef": "PAY-1001",
    "endpointUrl": "http://127.0.0.1:9095/hooks/paysetu",
    "status": "DELIVERED",
    "attempts": 2,
    "lastStatusCode": 200,
    "lastError": null,
    "nextAttemptAt": null,
    "deliveredAt": "2026-10-23T16:21:44.74506Z"
  },
  "attempts": [
    {
      "attemptedAt": "2026-10-23T16:21:14.503264Z",
      "statusCode": 503,
      "error": "HTTP 503",
      "durationMs": 80
    },
    {
      "attemptedAt": "2026-10-23T16:21:44.74506Z",
      "statusCode": 200,
      "error": null,
      "durationMs": 5
    }
  ]
}
```

### Case 13: the URL that is off

**Why:** still pending, waiting longer each time.

Request

``` code
GET /webhook-deliveries?status=PENDING HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 304

[
  {
    "id": 2,
    "eventId": "b8a6a692-952e-4abf-b6ac-717709d1e081",
    "type": "payment.captured",
    "paymentRef": "PAY-1001",
    "endpointUrl": "http://127.0.0.1:9096/hooks",
    "status": "PENDING",
    "attempts": 2,
    "lastStatusCode": null,
    "lastError": "could not connect",
    "nextAttemptAt": "2026-10-23T16:22:44.745001Z",
    "deliveredAt": null
  }
]
```

### Case 14: Meena reads Ravi's delivery

**Why:** `404`, the same as one that does not exist.

Request

``` code
GET /webhook-deliveries/1 HTTP/1.1
Authorization: Basic bWVlbmE6bWVlbmEtZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such delivery.",
  "instance": "/webhook-deliveries/1",
  "status": 404,
  "title": "Not Found"
}
```

### Case 15: ?status=LOST

**Why:** `400`.

Request

``` code
GET /webhook-deliveries?status=LOST HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to convert 'status' with value: 'LOST'",
  "instance": "/webhook-deliveries",
  "status": 400,
  "title": "Bad Request"
}
```

## What Ravi's server saw

Printed by `docs/test-merchant.py`, which recomputes each HMAC in Python: an independent check of the Java signing.

``` code
request 1: webhook-id b8a6a692-952e-4abf-b6ac-717709d1e081
  body {"type":"payment.captured","timestamp":"2026-10-23T16:21:14.241810Z","data":{"paymentRef":"PAY-1001","amountPaise":49900}}
  signature valid: yes, timestamp within 5 minutes: yes
  answered 503
request 2: webhook-id b8a6a692-952e-4abf-b6ac-717709d1e081
  body {"type":"payment.captured","timestamp":"2026-10-23T16:21:14.241810Z","data":{"paymentRef":"PAY-1001","amountPaise":49900}}
  signature valid: yes, timestamp within 5 minutes: yes
  answered 200
```

## The attempts table afterwards

``` code
 delivery_id |  at_utc  | status_code |       error       | duration_ms 
-------------+----------+-------------+-------------------+-------------
           2 | 16:21:14 |             | could not connect |          53
           1 | 16:21:14 |         503 | HTTP 503          |          80
           2 | 16:21:44 |             | could not connect |           3
           1 | 16:21:44 |         200 |                   |           5
(4 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                         | What happens                                                | Proved by                                                  |
|--------------------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------|
| The old way, merchant down                                   | One unsigned try, nothing to retry from                     | `theOldWayLosesThePaymentWhileTheMerchantIsDown`           |
| The merchant down for five minutes                           | Tries at 0, 30, 90, 210, 450 s; the fifth delivered; one id | `theApiKeepsThePaymentUntilTheMerchantIsBack`              |
| Register; the same URL; bad URLs; another merchant, same URL | `201`, `409`, `400`, `201`                                  | `anEndpointIsRegisteredWithASecretShownOnce`               |
| Headers, body and signature                                  | Exactly as specified; nothing sent inside the request       | `aPaymentIsSentSignedTheStandardWebhooksWay`               |
| Two URLs, one up, one down                                   | The log by status, every attempt                            | `theDeliveryLogListsByStatusAndShowsEveryAttempt`          |
| Always 500                                                   | Waits 30 s doubled; 8th failure final; never again          | `theWaitDoublesAfterEachFailureAndTheEighthFailureIsFinal` |
| Too slow, a redirect, nobody listening                       | A failed attempt each; the redirect not followed            | `aSlowMerchantARedirectOrNoServerIsAFailedAttempt`         |
| Two dispatcher rounds at once                                | Each delivery sent once                                     | `twoServersDispatchingAtOnceSendEachDeliveryOnce`          |
| A delivery another round has locked                          | Skipped, not waited for                                     | `aDeliveryAnotherRoundIsClaimingIsSkippedNotWaitedFor`     |
| The same payment twice; another amount                       | One event, one send; `409`                                  | `theSamePaymentReportedTwiceIsOneEventAndOneDelivery`      |
| No sign-in, another merchant's id                            | `401`, `403`, nothing stored                                | `withoutASignInIt401sAndAnotherMerchantsWebhooksAre403`    |
| Another merchant's deliveries                                | Not listed; `404`                                           | `aMerchantSeesOnlyTheirOwnDeliveries`                      |
| file:, javascript:, user names, CRLF, SQL in refs            | `400`, nothing stored                                       | `maliciousInputIsRefused`                                  |
| Tampered, other secret, replayed later                       | Verification fails                                          | `aForgedTamperedOrReplayedRequestFailsVerification`        |
| Rules written by plain SQL                                   | Refused by named constraints                                | `deliveryRulesHoldWithoutJava`                             |
| Deliveries cannot be written                                 | No event either                                             | `anEventWhoseDeliveriesCannotBeWrittenIsNotRecordedEither` |
| The real schedule and clock                                  | Sent without anyone calling the dispatcher                  | `theScheduledDispatcherSendsWithoutBeingAsked`             |

## The trap

Plausible but wrong

Fire-and-forget delivery with no signature, retry or delivery log.

- **The old way.** The test posts the payment once with `sendAsync` and never reads the answer. The merchant answers 503; ten minutes later it is back, and nothing comes: there is no record to retry from. The request had no signature, so a forged one would look the same.
- **The API.** The merchant is down for the first five minutes. Tries at 0 s, 30 s, 90 s, 210 s and 450 s; the fifth is answered 200. Every try is signed afresh and carries the same id.

While building, each part was undone once: a fixed 30 s wait turned 2 tests red; no attempt limit 1; no signature header 3; a new id on each try 2; following redirects 1; no per-attempt timeout 1; no timestamp check 1; no transaction around the event and its deliveries 1; any merchant's id 1; every merchant's deliveries listed 1; no amount check on repeats 1; user names allowed in URLs 1; payment refs not upper-cased 2. Removing `SKIP LOCKED` at first turned nothing red (see Tests); a test that holds a lock now catches it.

``` code
package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The merchant's server is down for five minutes. Written first. */
class FireAndForgetTrapTest extends ApiTest {

    /** The old way: post it right after the payment and never look at the answer. No signature, no retry, no log. */
    static CompletableFuture<HttpResponse<Void>> oldWay(String url, String body) {
        return HttpClient.newHttpClient().sendAsync(HttpRequest.newBuilder(URI.create(url)).header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body)).build(), HttpResponse.BodyHandlers.discarding());
    }

    @Test
    void theOldWayLosesThePaymentWhileTheMerchantIsDown() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            merchant.answer = () -> 503;   // down for maintenance
            oldWay(merchant.url(), "{\"type\":\"payment.captured\",\"data\":{\"paymentRef\":\"PAY-1001\",\"amountPaise\":49900}}").join();
            merchant.answer = () -> 200;   // back after five minutes
            CLOCK.advance(Duration.ofMinutes(10));
            dispatcher.dispatchDue();

            assertThat(merchant.received()).hasSize(1);   // the one try, answered 503, and never again
            assertThat(merchant.received().getFirst().signature()).isNull();   // and anyone could have sent it
            assertThat(jdbc.sql("SELECT count(*) FROM deliveries").query(Long.class).single()).isZero();   // nothing to retry from
        }
    }

    @Test
    void theApiKeepsThePaymentUntilTheMerchantIsBack() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            merchant.answer = () -> CLOCK.instant().isBefore(T0.plus(Duration.ofMinutes(5))) ? 503 : 200;
            String secret = secretFor("ravi", 1, merchant.url());
            testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());

            for (int second = 0; second <= 600; second += 10) {   // ten minutes, a dispatcher round every 10 s
                CLOCK.set(T0.plusSeconds(second));
                dispatcher.dispatchDue();
            }

            // Tried at once, then after 30 s, 1 min, 2 min and 4 min: the fifth try, 7.5 minutes in, is answered 200.
            assertThat(merchant.received()).extracting(r -> Duration.between(T0, r.at()).toSeconds()).containsExactly(0L, 30L, 90L, 210L, 450L);
            assertThat(merchant.received()).allMatch(r -> r.verifiedWith(secret));   // each try signed afresh
            assertThat(merchant.received()).extracting(TestMerchant.Received::id).containsOnly(merchant.received().getFirst().id());   // one id: the merchant can drop repeats
            var log = onlyDelivery("ravi");
            assertThat(log.at("/delivery/status").asString()).isEqualTo("DELIVERED");
            assertThat(log.at("/delivery/deliveredAt").asString()).isEqualTo("2026-10-23T10:07:30Z");
            assertThat(log.get("attempts")).extracting(a -> a.get("statusCode").asInt()).containsExactly(503, 503, 503, 503, 200);
        }
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                                           | Check with          |
|----------|-------------------------------------------------------------------|---------------------|
| JDK      | 25 (recommended). JDK 21 also works, see below                    | `java -version`     |
| Docker   | Docker Desktop (Windows, macOS) or Docker Engine (Linux), running | `docker info`       |
| Python 3 | Only for the test merchant in Try it yourself                     | `python3 --version` |
| Maven    | Not needed: the project ships the Maven wrapper                   |                     |

**macOS / Linux**

``` code
docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 17 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature (virtual threads are in 21).

## Try it yourself

Register a URL, start the test merchant with the secret you got, and record a payment:

``` code
curl -u ravi:ravi-demo-pass -H 'Content-Type: application/json' -d '{"url":"http://127.0.0.1:9095/hooks/paysetu"}' http://localhost:8080/merchants/1/webhook-endpoints
python3 docs/test-merchant.py 9095 whsec_...the-secret...
curl -u ravi:ravi-demo-pass -H 'Content-Type: application/json' -d '{"paymentRef":"PAY-1001","amountPaise":49900}' http://localhost:8080/merchants/1/test-events
```

The script answers 503 first: watch the retry arrive 30 seconds later, then read `GET /webhook-deliveries/1`. Stop the script and record another payment to watch the waits grow.

## Troubleshooting

| You see                                     | Cause                                                                                                                          | Fix                                                   |
|---------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| Every attempt says `could not connect`      | Nothing listens at the URL, or the app cannot reach it (from Docker, `127.0.0.1` is the container).                            | Start the merchant; use an address the app can reach. |
| The merchant says the signature is wrong    | The body was parsed and re-serialised before checking, or the secret's `whsec_` prefix was not removed before Base64-decoding. | Verify the raw bytes, with the decoded key.           |
| "timestamp within 5 minutes: NO"            | The merchant's clock is off.                                                                                                   | Sync it with NTP.                                     |
| `Could not find a valid Docker environment` | Docker is not running.                                                                                                         | Start Docker Desktop or the Docker service.           |

## Project layout

``` tree
stations/095-webhooks-to-merchants/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/paysetu/webhooks/
│   ├── SecurityConfig.java   ├── WebhookController.java   ├── Webhooks.java
│   ├── Dispatcher.java   ├── DispatchSchedule.java   ├── WebhookSignature.java
│   └── ProblemResponses.java   └── WebhooksApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__webhooks.sql
├── src/test/java/com/paysetu/webhooks/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, test merchant, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the dispatcher and the database behind it.

#### `src/main/java/com/paysetu/webhooks/SecurityConfig.java`

Does  
Who may do what.

Why  
HTTP Basic; merchants only; each sign-in belongs to one merchant.

Without it  
Anyone registering a URL for someone else's payments.

#### `src/main/java/com/paysetu/webhooks/WebhookController.java`

Does  
The four endpoints.

Why  
Checks the path's merchant against the sign-in, validates bodies, answers `202` for new payments and `200` for repeats.

Without it  
A merchant reading or redirecting another merchant's payments.

#### `src/main/java/com/paysetu/webhooks/Webhooks.java`

Does  
Endpoints, events and the log.

Why  
URL checks; the secret; the event and its deliveries in one transaction; a repeat returns the first event.

Without it  
A payment recorded with nobody to tell, or told twice.

- The payload is stored as text: the exact bytes that are signed and sent, not JSON that could be re-encoded differently.
- Payment refs are upper-cased with `Locale.ROOT`, so `pay-1001` is a repeat of `PAY-1001`.

#### `src/main/java/com/paysetu/webhooks/Dispatcher.java`

Does  
Sending, retrying, giving up.

Why  
Claims due deliveries in one statement, sends each on a virtual thread, records the attempt and the next one.

Without it  
A payment lost to a five-minute outage, or sent twice by two servers.

- The claim moves the next attempt past a lease (timeout + 30 s), so other rounds do not see it while we send. If this server dies mid-send, the lease runs out and another server tries again: at least once.
- The update checks `attempts` is still what we claimed; if another round got there first, ours is rolled back.
- Redirects are not followed: the merchant registered this URL.

#### `src/main/java/com/paysetu/webhooks/WebhookSignature.java`

Does  
Signing, and the merchant's check.

Why  
HMAC-SHA256 over id.timestamp.body; constant-time compare; 5-minute tolerance.

Without it  
Forged or replayed notifications.

#### `src/main/java/com/paysetu/webhooks/DispatchSchedule.java`

Runs a round every second after the last one ends (fixed delay, so rounds never pile up). Tests switch it off.

#### `src/main/java/com/paysetu/webhooks/ProblemResponses.java`

`401` and `403` in the same problem shape as other errors.

#### `src/main/resources/db/migration/V1__webhooks.sql`

Does  
Four tables.

Why  
Endpoints, events, deliveries (the outbox) and attempts, with named constraints.

Without it  
States the code would never write, from any writer.

#### `src/main/resources/application.yaml`

The demo rules: first retry, timeout, poll interval.

#### `src/main/java/com/paysetu/webhooks/WebhooksApplication.java`

Entry point, and the `Clock` every "now" comes from.

#### `compose.yaml`

PostgreSQL 17 for running the app.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                                                                                               | Result |
|---------------|-------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `WebhookContractTest` (3)                                                                                | pass   |
| Every station | Reproduce the failure before the fix                              | `FireAndForgetTrapTest` (2)                                                                              | pass   |
| Database      | Rollback and constraint tests against a real database             | `WebhookDatabaseTest` (2)                                                                                | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `WebhookSecurityTest` (4)                                                                                | pass   |
| Messaging     | Duplicate delivery, retry and dead letter                         | `RetryAndDeadLetterMessagingTest` (2), `DuplicateDeliveryMessagingTest` (2), `ScheduledDeliveryTest` (1) | pass   |
| Idempotency   | Replay: the same request twice gives one effect                   | `PaymentReplayTest` (1)                                                                                  | pass   |

An hour of retries runs in milliseconds: the app takes "now" from a `Clock`, the tests move a `TestClock` by hand and run dispatcher rounds themselves, with the schedule switched off. One test keeps the real schedule and clock, and waits for the delivery with Awaitility instead of a fixed sleep.

Found while building: with `FOR UPDATE SKIP LOCKED` removed, the two-rounds-at-once test still passed. The claim is one short statement, and the lease it writes already hides the rows from the next round, so the two rounds almost never meet inside it. A second test holds a lock on one delivery, as a round in the middle of its claim would, and checks that the dispatcher takes the other one at once instead of waiting: that one fails without `SKIP LOCKED`.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.webhooks.RetryAndDeadLetterMessagingTest
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.webhooks.PaymentReplayTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.webhooks.WebhookDatabaseTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.webhooks.WebhookContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.webhooks.DuplicateDeliveryMessagingTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.webhooks.WebhookSecurityTest
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.webhooks.ScheduledDeliveryTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.paysetu.webhooks.FireAndForgetTrapTest
[INFO] Tests run: 17, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/paysetu/webhooks/FireAndForgetTrapTest.java`

Written first: the old way against the API, with the merchant down for five minutes.

#### `src/test/java/com/paysetu/webhooks/WebhookContractTest.java`

Registering, the exact request a merchant receives, the delivery log.

#### `src/test/java/com/paysetu/webhooks/RetryAndDeadLetterMessagingTest.java`

Every wait, one second early and on time; the dead letter; timeouts, redirects, no server.

#### `src/test/java/com/paysetu/webhooks/DuplicateDeliveryMessagingTest.java`

Two rounds at once; a delivery locked by another round skipped.

#### `src/test/java/com/paysetu/webhooks/PaymentReplayTest.java`

The same payment reported twice: one event, one send; another amount 409.

#### `src/test/java/com/paysetu/webhooks/WebhookSecurityTest.java`

401, 403, another merchant's data, malicious input, forged and replayed signatures.

#### `src/test/java/com/paysetu/webhooks/WebhookDatabaseTest.java`

Named constraints with plain SQL; the event and its deliveries commit together.

#### `src/test/java/com/paysetu/webhooks/ScheduledDeliveryTest.java`

The real schedule and clock.

#### `src/test/java/com/paysetu/webhooks/TestMerchant.java`

A merchant's server: records what arrives, answers what the test says.

#### `src/test/java/com/paysetu/webhooks/TestClock.java`

A clock moved by hand.

#### `src/test/java/com/paysetu/webhooks/ApiTest.java`

Shared setup: empty tables and the clock at 10:00 UTC before each test, the scheduler off.

#### `src/test/java/com/paysetu/webhooks/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/paysetu/webhooks/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RetryDeadDeliveryChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 17 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 21 tests pass (17 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Send a dead letter again

`POST /webhook-deliveries/{id}/retry`: a `FAILED` delivery goes back to `PENDING` with zero attempts, due now, and the old attempts stay in the log. Any other state is `409`; another merchant's delivery `404`.

**Done when:** both tests in `RetryDeadDeliveryChallengeTest` pass.

Hints

- One UPDATE with `WHERE status = 'FAILED'` and the merchant check; 0 rows means 404 or 409: read the row to tell which.
- The database already allows it: attempts 0 with a next attempt is a valid pending row.
- A new matcher in `SecurityConfig`: everything not listed is denied.

#### `challenge/RetryDeadDeliveryChallengeTest.java`

``` code
package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: POST /webhook-deliveries/{id}/retry sends a dead-lettered delivery again, from the first attempt. */
class RetryDeadDeliveryChallengeTest extends ApiTest {

    @Test
    void aFailedDeliveryCanBeSentAgainOnceTheMerchantIsFixed() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            merchant.answer = () -> 500;
            secretFor("ravi", 1, merchant.url());
            testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());
            for (int i = 0; i < 8; i++) {   // eight failures, an hour apart: dead-lettered
                dispatcher.dispatchDue();
                CLOCK.advance(Duration.ofHours(1));
            }
            deliveries("ravi", "?status=FAILED").andExpect(jsonPath("$.length()").value(1));

            merchant.answer = () -> 200;   // the merchant fixed their server
            mvc.perform(post("/webhook-deliveries/1/retry").with(httpBasic("ravi", password("ravi")))).andExpect(status().isAccepted())
                    .andExpect(jsonPath("$.status").value("PENDING")).andExpect(jsonPath("$.attempts").value(0))
                    .andExpect(jsonPath("$.nextAttemptAt").value("2026-10-23T18:00:00Z"));
            assertThat(dispatcher.dispatchDue()).isEqualTo(1);

            deliveries("ravi", "?status=DELIVERED").andExpect(jsonPath("$.length()").value(1));
            assertThat(onlyDelivery("ravi").get("attempts")).hasSize(9);   // the history is kept
        }
    }

    @Test
    void onlyYourOwnFailedDeliveriesCanBeRetried() throws Exception {
        secretFor("ravi", 1, "https://ravi-kirana.example/hooks/paysetu");
        testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());
        mvc.perform(post("/webhook-deliveries/1/retry").with(httpBasic("ravi", password("ravi")))).andExpect(status().isConflict());   // still pending
        mvc.perform(post("/webhook-deliveries/1/retry").with(httpBasic("meena", password("meena")))).andExpect(status().isNotFound());
        mvc.perform(post("/webhook-deliveries/99/retry").with(httpBasic("ravi", password("ravi")))).andExpect(status().isNotFound());
        mvc.perform(post("/webhook-deliveries/1/retry")).andExpect(status().isUnauthorized());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 40 minutes

## Rotate the secret

`POST /merchants/{id}/webhook-endpoints/{endpointId}/secret` gives the endpoint a new secret (`201`). For 24 hours every request carries two signatures, new and old, separated by a space, so the merchant can switch over without rejecting a payment. After that, only the new one.

**Done when:** both tests in `RotateSecretChallengeTest` pass.

Hints

- A V2 migration: `previous_secret` and `previous_secret_until`, both set or both empty (a CHECK).
- The claim can return the old secret only while it is valid: `CASE WHEN previous_secret_until > :now THEN previous_secret END`.
- `verify` already accepts any one of several signatures.

#### `challenge/RotateSecretChallengeTest.java`

``` code
package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /merchants/{id}/webhook-endpoints/{endpointId}/secret gives the endpoint a new secret. For 24
 * hours each request carries two signatures, so the merchant can switch over without missing a payment.
 */
class RotateSecretChallengeTest extends ApiTest {

    String rotate(String user, long merchantId, long endpointId) throws Exception {
        return json(mvc.perform(post("/merchants/{m}/webhook-endpoints/{e}/secret", merchantId, endpointId).with(httpBasic(user, password(user))))
                .andExpect(status().isCreated())).get("secret").asString();
    }

    @Test
    void bothSecretsWorkForADayThenOnlyTheNewOne() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            String old = secretFor("ravi", 1, merchant.url());
            String fresh = rotate("ravi", 1, 1);
            assertThat(fresh).startsWith("whsec_").isNotEqualTo(old);

            testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());
            CLOCK.advance(Duration.ofHours(23));
            dispatcher.dispatchDue();
            var duringSwitch = merchant.received().getLast();
            assertThat(duringSwitch.verifiedWith(old)).isTrue();
            assertThat(duringSwitch.verifiedWith(fresh)).isTrue();

            testEvent("ravi", 1, "PAY-1002", 49900).andExpect(status().isAccepted());
            CLOCK.advance(Duration.ofHours(2));   // 25 hours after the rotation
            dispatcher.dispatchDue();
            var afterADay = merchant.received().getLast();
            assertThat(afterADay.verifiedWith(old)).isFalse();
            assertThat(afterADay.verifiedWith(fresh)).isTrue();
        }
    }

    @Test
    void onlyYourOwnEndpointsSecretCanBeChanged() throws Exception {
        secretFor("meena", 2, "https://meena-dhaba.example/hooks");
        mvc.perform(post("/merchants/2/webhook-endpoints/1/secret").with(httpBasic("ravi", password("ravi")))).andExpect(status().isForbidden());
        mvc.perform(post("/merchants/1/webhook-endpoints/1/secret").with(httpBasic("ravi", password("ravi")))).andExpect(status().isNotFound());
        mvc.perform(post("/merchants/2/webhook-endpoints/1/secret")).andExpect(status().isUnauthorized());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A merchant that is gone for a week

One merchant's server has been off for a week. Every payment makes a delivery that fails eight times. Design what happens: when do you stop sending to that endpoint, how do you tell the merchant, and how do they get the missed payments once they are back (a retry per delivery, a "replay since" button, or a list endpoint they poll)? And a merchant that needs payment events in order: what would you change?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old way and the five-minute outage.
2.  Write the tables and their constraints; the event and its deliveries in one transaction.
3.  Write the signature and its check, with tests for tampering and replay.
4.  Write the dispatcher: claim, send, record; then the backoff and the dead letter; then two rounds at once.

## Design alternatives and trade-offs

| Approach                                             | What it costs                                                                                                                     | Verdict         |
|------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|-----------------|
| An outbox table and a scheduled dispatcher           | A poll every second; at-least-once, so merchants must drop repeats.                                                               | Chosen          |
| Post right after the payment, once                   | Lost on any outage; no proof of what was sent.                                                                                    | The trap        |
| Post inside the payment's transaction                | A slow merchant holds the payment's transaction and connection; a rollback after posting announces a payment that did not happen. | Avoid           |
| A message broker (Kafka, RabbitMQ) with retry topics | Another system to run; the outbox is still needed to publish atomically.                                                          | At larger scale |
| Fixed retry every 30 s, forever                      | Hammers a merchant that is down; never tells anyone it failed.                                                                    | Review finding  |

## Database design

| Object                                                         | What                                        | Why                                                                           |
|----------------------------------------------------------------|---------------------------------------------|-------------------------------------------------------------------------------|
| `events_once_per_object`                                       | UNIQUE (merchant, type, payment ref)        | A payment reported twice is one event.                                        |
| `deliveries_once_per_endpoint`                                 | UNIQUE (event, endpoint)                    | Never two deliveries of one event to one URL.                                 |
| `deliveries_attempts_range`                                    | CHECK 0..8                                  | The attempt limit, for any writer.                                            |
| `deliveries_pending_has_next`, `deliveries_delivered_has_time` | CHECKs                                      | Pending exactly when a next attempt is set; delivered exactly when a time is. |
| `deliveries_due`                                               | Partial index on next attempt, pending only | The dispatcher's query reads only what is waiting.                            |
| `endpoints_url_http`, `endpoints_secret_format`                | CHECKs                                      | Only web URLs; only generated secrets.                                        |

**Transaction boundaries:** the event and its deliveries commit together. The claim is one autocommitted statement. Each attempt and the delivery's new state commit together, after the HTTP call: no transaction is open while we wait for a merchant.

``` code
-- Where each merchant wants to hear about its payments. The secret signs every request (it cannot be hashed:
-- we need it to sign). shortcut: stored as is; encrypt it with a key from a KMS in production.
CREATE TABLE webhook_endpoints (
    id          bigserial PRIMARY KEY,
    merchant_id bigint      NOT NULL,
    url         text        NOT NULL,
    secret      text        NOT NULL,
    created_at  timestamptz NOT NULL,
    CONSTRAINT endpoints_url_once_per_merchant UNIQUE (merchant_id, url),
    CONSTRAINT endpoints_url_http CHECK (url ~ '^https?://[^/@]+' AND length(url) <= 2000),
    CONSTRAINT endpoints_secret_format CHECK (secret ~ '^whsec_[A-Za-z0-9+/]{32}$')
);

-- What happened, written once. A payment is captured once, so it makes one event, however often it is reported.
CREATE TABLE events (
    id           uuid        PRIMARY KEY,
    merchant_id  bigint      NOT NULL,
    type         text        NOT NULL,
    object_ref   text        NOT NULL,
    amount_paise bigint      NOT NULL,
    payload      text        NOT NULL,   -- the exact bytes we sign and send, not re-encoded JSON
    created_at   timestamptz NOT NULL,
    CONSTRAINT events_once_per_object UNIQUE (merchant_id, type, object_ref),
    CONSTRAINT events_type CHECK (type IN ('payment.captured')),
    CONSTRAINT events_amount_positive CHECK (amount_paise > 0)
);

-- One event to one endpoint: the outbox the dispatcher works through.
CREATE TABLE deliveries (
    id               bigserial   PRIMARY KEY,
    event_id         uuid        NOT NULL REFERENCES events,
    endpoint_id      bigint      NOT NULL REFERENCES webhook_endpoints,
    status           text        NOT NULL DEFAULT 'PENDING',
    attempts         int         NOT NULL DEFAULT 0,
    next_attempt_at  timestamptz,
    last_status_code int,
    last_error       text,
    delivered_at     timestamptz,
    CONSTRAINT deliveries_once_per_endpoint UNIQUE (event_id, endpoint_id),
    CONSTRAINT deliveries_status CHECK (status IN ('PENDING', 'DELIVERED', 'FAILED')),
    CONSTRAINT deliveries_attempts_range CHECK (attempts BETWEEN 0 AND 8),
    CONSTRAINT deliveries_pending_has_next CHECK ((status = 'PENDING') = (next_attempt_at IS NOT NULL)),
    CONSTRAINT deliveries_delivered_has_time CHECK ((status = 'DELIVERED') = (delivered_at IS NOT NULL))
);
CREATE INDEX deliveries_due ON deliveries (next_attempt_at) WHERE status = 'PENDING';

-- Every try, kept for the merchant to read: when, what came back, how long it took.
CREATE TABLE delivery_attempts (
    id           bigserial   PRIMARY KEY,
    delivery_id  bigint      NOT NULL REFERENCES deliveries,
    attempted_at timestamptz NOT NULL,
    status_code  int,
    error        text,
    duration_ms  int         NOT NULL,
    CONSTRAINT attempts_duration_positive CHECK (duration_ms >= 0)
);
CREATE INDEX delivery_attempts_by_delivery ON delivery_attempts (delivery_id, id);
```

# 3 · Go deeper: Production

Where URLs point  
A webhook URL is user input your server will call. Check the address it resolves to on every attempt (no private, loopback or metadata addresses), as an SSRF-safe fetcher does. Not done here: a demo rule.

Secrets  
The secret must be readable to sign, so it cannot be hashed: encrypt it at rest with a key from a KMS. Here it is stored as is.

Jitter  
After a big outage every delivery retries on the same schedule. Add a random part to each wait so they spread out.

Merchants who are gone  
Disable an endpoint after days of failures and email the merchant (challenge 3).

Clean-up  
Events, deliveries and attempts grow forever here. Keep them for a set time, then delete or archive.

Monitoring  
Alert on the age of the oldest pending delivery and on the number of failures per merchant.

# 3 · Go deeper: Interview

## Interview takeaways

How do you make sure a webhook is not lost?

Write it to an outbox table in the same transaction as the change, and send it from a background job that retries until a 2xx or a limit.

Exactly once or at least once?

At least once: a timeout after the merchant processed it means we send again. Send a stable id so the receiver can drop repeats.

How does the merchant know a webhook is from you?

An HMAC-SHA256 signature over the id, a timestamp and the raw body, with a shared secret; compared in constant time.

Why sign the timestamp?

So a captured request cannot be replayed later: the receiver refuses timestamps older than a few minutes.

Why exponential backoff?

A merchant that is down gets fewer and fewer requests, and the retries still cover a long outage: 8 tries over about an hour here.

How do two servers avoid sending the same row?

Claim rows with FOR UPDATE SKIP LOCKED and move them past a lease in the same statement.

## Self-check rubric

| Area        | Meets the bar        | Above the bar                                                                    |
|-------------|----------------------|----------------------------------------------------------------------------------|
| Correctness | All 17 tests pass.   | You ran the flawed version and explained each failure.                           |
| Delivery    | Retries on failure.  | Outbox in one transaction, backoff, dead letter, at-least-once with a stable id. |
| Security    | Requests are signed. | Timestamp in the signature, constant-time check, secrets per endpoint.           |
| Testing     | A retry test.        | A clock you move, parallel rounds, and one test with the real schedule.          |

# 3 · Go deeper: Review

## The pull request

A teammate simplifies the dispatcher: a plain SELECT of what is due instead of the "complicated" UPDATE, "since the update after sending moves it on anyway", and a retry every 30 seconds until it works, "because merchants want every payment". Read the file and list every problem before opening the findings.

#### `review/Dispatcher.java`

``` code
package com.paysetu.webhooks;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.io.IOException;
import java.net.ConnectException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Executors;

/** Works through the outbox: reads the deliveries that are due, sends each one signed, and records every attempt. */
@Component
class Dispatcher {

    static final int BATCH = 20;
    private static final Logger log = LoggerFactory.getLogger(Dispatcher.class);

    private final JdbcClient jdbc;
    private final Clock clock;
    private final TransactionTemplate tx;
    private final Duration firstRetry;
    private final Duration timeout;
    private final HttpClient http;

    Dispatcher(JdbcClient jdbc, Clock clock, PlatformTransactionManager transactions,
               @Value("${paysetu.webhooks.first-retry}") Duration firstRetry, @Value("${paysetu.webhooks.timeout}") Duration timeout) {
        this.jdbc = jdbc;
        this.clock = clock;
        this.tx = new TransactionTemplate(transactions);
        this.firstRetry = firstRetry;
        this.timeout = timeout;
        // Redirects are not followed: the merchant registered this URL, not wherever it points us next.
        this.http = HttpClient.newBuilder().connectTimeout(timeout).followRedirects(HttpClient.Redirect.NEVER).build();
    }

    record Due(long id, int attempts, UUID eventId, String payload, String url, String secret) {
    }

    /** One round. Returns how many deliveries it tried. */
    int dispatchDue() {
        List<Due> due = claim(now());
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {   // one slow merchant does not hold up the rest
            for (Due d : due) {
                threads.execute(() -> {
                    try {
                        attempt(d);
                    } catch (RuntimeException e) {
                        log.warn("Delivery {} could not be recorded", d.id(), e);
                    }
                });
            }
        }
        return due.size();
    }

    /** Simpler: read what is due. The update after sending moves it on, so it is not sent twice. */
    private List<Due> claim(OffsetDateTime now) {
        return jdbc.sql("""
                        SELECT d.id, d.attempts, e.id AS event_id, e.payload, w.url, w.secret
                        FROM deliveries d JOIN events e ON e.id = d.event_id JOIN webhook_endpoints w ON w.id = d.endpoint_id
                        WHERE d.status = 'PENDING' AND d.next_attempt_at <= :now
                        ORDER BY d.next_attempt_at, d.id LIMIT :batch""")
                .param("now", now).param("batch", BATCH)
                .query(Due.class).list();
    }

    private void attempt(Due d) {
        OffsetDateTime at = now();
        String id = d.eventId().toString();
        long timestamp = at.toEpochSecond();
        HttpRequest request = HttpRequest.newBuilder(URI.create(d.url())).timeout(timeout)
                .header("Content-Type", "application/json")
                .header("User-Agent", "Paysetu-Webhooks/1.0")
                .header("webhook-id", id)   // the same on every retry: the merchant drops repeats by it
                .header("webhook-timestamp", Long.toString(timestamp))
                .header("webhook-signature", WebhookSignature.sign(d.secret(), id, timestamp, d.payload()))
                .POST(HttpRequest.BodyPublishers.ofString(d.payload())).build();
        long started = System.nanoTime();
        Integer code = null;
        String error = null;
        try {
            code = http.send(request, HttpResponse.BodyHandlers.discarding()).statusCode();
            if (code / 100 != 2) {
                error = "HTTP " + code + (code / 100 == 3 ? " (redirects are not followed)" : "");
            }
        } catch (HttpTimeoutException e) {
            error = "timed out after " + timeout.toMillis() + " ms";
        } catch (ConnectException e) {
            error = "could not connect";
        } catch (IOException e) {
            error = e.getClass().getSimpleName();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return;
        }
        record(d, at, code, error, (int) ((System.nanoTime() - started) / 1_000_000));
    }

    private void record(Due d, OffsetDateTime at, Integer code, String error, int durationMs) {
        int attempts = d.attempts() + 1;
        String status = error == null ? "DELIVERED" : "PENDING";   // merchants want every payment: keep trying until it works
        OffsetDateTime next = status.equals("PENDING") ? at.plus(firstRetry) : null;   // every 30 s, so it arrives soon after they are back
        tx.executeWithoutResult(s -> {
            jdbc.sql("INSERT INTO delivery_attempts (delivery_id, attempted_at, status_code, error, duration_ms) VALUES (?, ?, ?, ?, ?)")
                    .params(d.id(), at, code, error, durationMs).update();
            jdbc.sql("""
                            UPDATE deliveries SET status = ?, attempts = ?, next_attempt_at = ?, last_status_code = ?, last_error = ?, delivered_at = ?
                            WHERE id = ?""")
                    .params(status, attempts, next, code, error, status.equals("DELIVERED") ? at : null, d.id()).update();
        });
    }

    private OffsetDateTime now() {
        return OffsetDateTime.now(clock).withOffsetSameInstant(ZoneOffset.UTC).truncatedTo(ChronoUnit.MICROS);
    }
}
```

## Findings

1Two servers send the same delivery

"The update after sending moves it on": but between the SELECT and that update, the HTTP call takes as long as the merchant does. Another server's round, a second later, reads the same rows and sends them again. Every app with two instances sends duplicates. The claim must move the row on before sending, in the same statement that picks it (here: a lease, with SKIP LOCKED).

**Test evidence:** `twoServersDispatchingAtOnceSendEachDeliveryOnce` and `aDeliveryAnotherRoundIsClaimingIsSkippedNotWaitedFor` fail.

2Retrying every 30 seconds, forever

"So it arrives soon after they are back": and a merchant that is down for a day gets 2,880 requests per payment, all at once when it comes back. The waits must grow. And "never give up" hides the problem: nobody is told the delivery failed. Worse, the database's limit of 8 attempts makes the ninth try's record fail: the row is unchanged and still due, so it is sent again on every round, every second.

**Test evidence:** `theWaitDoublesAfterEachFailureAndTheEighthFailureIsFinal` and `theApiKeepsThePaymentUntilTheMerchantIsBack` fail.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                        | Fixed version | Flawed version |
|-----------------------------------|---------------|----------------|
| `PaymentReplayTest`               | 1 / 1         | 1 / 1          |
| `ScheduledDeliveryTest`           | 1 / 1         | 1 / 1          |
| `WebhookContractTest`             | 3 / 3         | 3 / 3          |
| `WebhookDatabaseTest`             | 2 / 2         | 2 / 2          |
| `WebhookSecurityTest`             | 4 / 4         | 4 / 4          |
| `DuplicateDeliveryMessagingTest`  | 2 / 2         | 0 / 2          |
| `FireAndForgetTrapTest`           | 2 / 2         | 1 / 2          |
| `RetryAndDeadLetterMessagingTest` | 2 / 2         | 1 / 2          |

With one server and a merchant that is up, the flawed dispatcher delivers every payment. Its problems need a second instance and an outage: both normal in production.
