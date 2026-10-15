# Station 032 plan: Return and refund eligibility

**Problem.** Kartwala's refund rules lived in one method with no tests but a happy path. In March electronics moved
from 30 to 7 days, edited in a switch case clothing shared, so clothing returns on day 8 to 30 were refused.

**Endpoint.** `POST /refund-eligibility-checks` {orderId, reason, tagsAttached?, sealIntact?} 200 {orderId,
eligible, reasons[], refundPaise, lastDayToReturn}; 404 unknown order; 400 bad id, unknown reason, missing reason,
unknown field, missing tags answer for clothing or seal answer for electronics.

**Design for testing.** `RefundRules.check(order, reason, tags, seal, today)` is a pure function; `Category` owns its
window and accepted reasons (demo rules: clothing 30, electronics 7, books 10, grocery 2); `RefundService` alone knows
"today" (a `Clock` bean, India's calendar) and calls `OrderLookup` (query) and `EligibilityAudit` (command).
Demo orders are delivered N days before startup, so captures read the same any day.

**Trap.** `HappyPathOnlyTrapTest`: the old suite's only test still passes on the old switch; clothing on day 20 was
refused; electronics keeps 7 days. Mutations: clothing 7 days -> 5 red; no hygiene rule -> 3; server date instead of
India -> 1; fee on every reason -> 2; no audit -> 1; seal blocks damaged -> 2; only the first reason -> 2.

**Tests.** Trap; `RefundRulesTest` (CsvSource table, EnumSource boundaries, hygiene, fee, undelivered);
`RefundServiceTest` (Mockito strict stubs: stub the query, verify the command; India's date); `RefundContractTest`
(fixed Clock bean, HTTP).

**Practice.** 1: FOOTWEAR without touching clothing. 2: festive extension with boundary dates. Design: who owns the
rule table, and could business people edit it safely?
