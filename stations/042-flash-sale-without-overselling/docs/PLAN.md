# Station 042 plan: Flash sale without overselling

**Problem.** Kartwala sold 517 of 500 phones: the code read the stock, checked it in Java, then updated, and
concurrent buyers all read the same stock.

**Endpoint.** `POST /flash-sales/{saleId}/purchases` {customerId C-NNNNNN} 201 {purchaseId, saleId, customerId,
pricePaise}; 409 Sold out / Sale ended / Not started / Already bought; 404 unknown sale; 400 bad body or id. A purchase
record is created; no payment is taken.

**Code.** One transaction: `UPDATE flash_sales SET stock_left = stock_left - 1 WHERE id = ? AND stock_left > 0 AND
now() in window`; rows affected 0 -> no phone, explain why from a read; else INSERT purchase (unique per customer;
a duplicate rolls back the UPDATE).

**Database.** flash_sales checks: stock_not_negative, stock_within_total, price_positive, window_order. purchases:
sale FK, purchases_one_per_customer.

**Trap.** `OversellTrapTest`: old read-check-update on a table with no constraint, 100 buyers for 5 phones, sells
more than 5 and the stock goes negative (3 of 3 runs while building); the conditional update sells exactly 5.
Mutations: no stock condition -> 4 errors (the CHECK refuses: 500s); no transaction -> 2 red; rows ignored -> 4;
read-check-write-the-value -> 2.

**Tests.** `FlashSaleConcurrencyTest` (500 buyers for 50 via HTTP; one customer 20 times), `FlashSaleDatabaseTest`,
`PurchaseContractTest`. Capture: 300 curl buyers for 50 phones against the running app.

**Review.** review/FlashSaleStore.java ignores rows affected and drops @Transactional; review/PurchaseController.java
says "Sold out" for every refusal. 6 of 10 fail.

**Practice.** 1: GET /flash-sales/{id} with status from SQL CASE. 2: cancel returns the phone once, 10 at a time.
Design: 20,000 buyers a second on one row.
