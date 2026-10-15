# Station 039 plan: Human-friendly order numbers

**Problem.** Tiffino's customers read UUIDs out to support. The replacement, a counter in memory, started again at
1 after every restart and ran separately on each server, so two orders shared a number.

**Endpoints.** `POST /orders` {outletId TF-NN, totalPaise} 201 {orderNumber, outletId, totalPaise} + Location;
400 bad body. `GET /orders/by-number/{number}` any case, with or without spaces/dashes: 200; 400 not shaped like an
order number; 400 check digit wrong ("one digit is probably wrong", no lookup); 404 valid but unknown.

**Numbers.** `TF-` + 7 digits from `order_number_seq` (1000001..9999999, NO CYCLE) + `-` + Luhn check digit.
`orders_number_unique`, `orders_number_format`, `orders_total_positive`. Internal identity id never shown.

**Trap.** `InMemoryCounterTrapTest`: two servers with their own counters both issue "#1"; a restart issues "#1"
again; two OrderNumbers on one database plus a "restarted" third issue 101 distinct numbers; a repeat would hit the
unique constraint.

**Tests.** `CheckDigitTest` (ISO/IEC 7812-1 example 7992739871 -> 3; every single wrong digit caught; adjacent swaps
caught except 09/90), `OrderNumberConcurrencyTest` (100 parallel orders: distinct, valid, no failures),
`OrderDatabaseTest` (named constraints; a rolled-back order leaves a gap; NO CYCLE), `OrderContractTest`.

**Review.** review/OrderNumbers.java: max()+1 instead of the sequence ("no gaps"), digit-sum check digit, lookups
case-sensitive. 7 of 17 tests fail (docs/review-run.txt).

**Practice.** 1: a public UUID per order (V2) and GET /orders/{orderId}. 2: daily kitchen tokens per outlet with an
atomic upsert (V3), 50 in parallel. Design: numbers across regions.
