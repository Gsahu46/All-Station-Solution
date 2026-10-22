# Station 086 plan: One API for many payment providers

**Problem.** Paysetu (fictional) took four months to switch payment provider: provider calls, amounts and error codes
were spread through the code. The first "multi-provider" version failed over to the second provider on any error,
including a timeout after the first had already charged: some customers were charged twice.

**Endpoints.** `POST /payments` {orderId, amountPaise}: one payment per order (case-insensitive, stored upper case).
201 succeeded, 402 declined (reason), 202 unknown (a provider may have charged and could not say), 503 failed (no
provider reached). The same order again: the same status and body, nothing charged again; another amount 409.
`POST /payments/{id}/refunds` {amountPaise}: to the provider that took the payment; 201; more than is left or not a
succeeded payment 409; unknown 404; provider unreachable 503 and the amount is freed.

**Adapters.** `PaymentProvider` (charge, lookup, refund; outcomes Charged/Declined; exceptions NotSent/Unknown).
`AlphaProvider` over the simulated `AlphaApi` (rupee text, CAPTURED/FAILED, word codes); `BetaProvider` over
`BetaApi` (paise, two-digit response codes). `Providers` picks by `paysetu.primary` / `paysetu.fallback`; a wrong
name stops the start.

**Rule.** NotSent: try the next provider. Unknown: ask the same provider (lookup); charged or declined is the answer;
"no such charge" lets the next one be tried; lookup failing too: "unknown", no other provider. A decline is never
failed over. Limit (shortcut comment): one lookup straight after the timeout.

**Database.** payments: order once, order shape, amount > 0, known provider, status, succeeded has ref, declined has
reason, refunds within amount, refunds only when paid. refunds: FK, amount > 0, status, succeeded has ref.

**Trap.** `FailoverAfterTimeoutTrapTest`: the old logic run against the simulations charges both; the API asks
first, finds the charge, and never calls sim-beta.

**Found while building.** (1) Removing the refund row lock changed no test: the CHECK caught the second refund as a
500. A parallel refund test with a 200 ms reservation trigger now fails without the lock. (2) The captures could not
show a timeout without a control endpoint: demo amounts ending in 97 and 98 paise make sim-alpha time out after
charging or refuse the connection. (3) Removing the duplicate-order catch passed in one run and failed in another:
a 200 ms insert trigger in the five-at-once test makes it fail every time.

**Mutations.** no status check -> 4; timeout moves on -> 2; decline moves on -> 3; refund via primary -> 1; no refund
lock -> 1; no duplicate-order catch -> 1; no give-back -> 1; amount check -> 1; alpha funds code -> 3; beta 62 -> 1;
rupees without paise -> 8.

**Review.** "Resilience": any error fails over; refunds through the current primary (count in docs/review-run.txt).

**Practice.** 1: status check for unknown payments. 2: a third adapter, sim-gamma, by config and a V3 migration.
3 (paper): routing by method and success rate, and webhooks.
