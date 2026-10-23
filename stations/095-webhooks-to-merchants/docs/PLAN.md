# Station 095 plan: Webhooks to merchants

**Problem.** Paysetu (fictional payments company): merchants miss "payment captured" notifications when their server
is down for five minutes. The old code posted once, right after the payment, and never looked at the answer: no
signature (anyone could post a fake "paid"), no retry, no record.

**Endpoints.** `POST /merchants/{id}/webhook-endpoints {url}` 201 with the signing secret (shown once); 400 not
http(s), no host, user name or #fragment, over 2000 chars; 409 the same URL again. `POST /merchants/{id}/test-events
{paymentRef, amountPaise}` (demo helper, like a dashboard's "send test webhook": records a captured payment, no payment
exists) 202 with the event id; the same payment again 200, the same event; another amount 409. `GET
/webhook-deliveries?status=PENDING|DELIVERED|FAILED` the merchant's deliveries, newest first (100). `GET
/webhook-deliveries/{id}` one delivery and every attempt; 404 for another merchant's. HTTP Basic: ravi (merchant 1),
meena (merchant 2); another merchant's id 403; none 401.

**Outbox.** The event and one delivery per endpoint are written in one transaction; nothing is sent in the request.
A dispatcher (@Scheduled, fixed delay 1 s) claims due deliveries with one UPDATE (FOR UPDATE SKIP LOCKED, next attempt
moved past a lease), sends them on virtual threads, and records each attempt. 2xx delivered; anything else (3xx not
followed, 4xx, 5xx, timeout 5 s, no connection) a failure: wait 30 s, doubled each time; the 8th failure is final
(FAILED, dead letter). Database: attempts 0..8, PENDING iff a next attempt, DELIVERED iff a time, one delivery per
event and endpoint, one event per payment.

**Signature.** Standard Webhooks (community specification): webhook-id (the event id, the same on every retry),
webhook-timestamp, webhook-signature v1,base64(HMAC-SHA256(id.timestamp.body)). WebhookSignature.verify is the
merchant's side: constant-time compare, 5-minute tolerance.

**Trap.** `FireAndForgetTrapTest`: the old way, merchant down: one try, unsigned, nothing to retry. The API: tries at
0, 30, 90, 210, 450 s; the fifth (7.5 min) is answered 200; all signed, one id.

**Tests.** A test clock moved by hand (no sleeping), the scheduler off, a merchant server per test; one test with the
real schedule and clock (Awaitility). Two dispatcher rounds in parallel; a delivery locked by another round.

**Review.** Plain SELECT of due rows, fixed 30 s retry, never gives up.

**Practice.** 1: POST /webhook-deliveries/{id}/retry for a FAILED delivery. 2: rotate the secret, both signatures for
24 h (V2). 3 (paper): disabling endpoints that fail for days, and ordering.
