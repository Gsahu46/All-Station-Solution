# Station 055 plan: Checkout as one transaction

**Problem.** Kartwala's checkout() had no @Transactional and called this.placeOrder(), which did. Self-invocation
bypasses Spring's proxy, so no transaction started: each statement committed alone. When the second line was out of
stock, the order and the payment record (saved first) and the first line's reservation stayed: paid orders with
half their stock reserved.

**Endpoints.** `POST /checkouts` {customerId, lines 1-20 [{productId, quantity 1-10}]} 201 + Location with total,
payment record (CAPTURED, simulated) and lines; 409 not enough stock; 422 unknown or repeated product; 400 malformed.
`GET /checkouts/{id}` (readOnly) 200/404.

**Code.** CheckoutService.checkout is @Transactional and called by the controller through the proxy; reservations are
conditional UPDATEs (stock >= quantity); the payment record is written last; all failures are unchecked
(ErrorResponseException), so they roll back.

**Database.** products_stock_not_negative, products_price_positive, orders_total_positive, orders_status_known,
reservations_* (FKs, one per product, quantity 1-10), payments_* (FK, one per order, positive, status known).

**Tests.** SelfInvocationTrapTest (the old class registered as a real proxied bean: through checkout() the state is
1/1/1/48/5; through placeOrder() via the proxy, everything rolls back; the fixed API rolls back whole),
CheckoutContractTest, CheckoutDatabaseTest (constraints; a checked exception commits unless rollbackFor; unchecked
rolls back; readOnly refuses writes). Mutations: no @Transactional -> 2 red; reserve without the stock condition -> 2
(the check constraint fires as a 500); a non-transactional wrapper calling this.checkout() -> 2.

**Practice.** 1: cancellation in one transaction. 2: a checked PaymentDeclined that must roll back (without
rollbackFor: 1/1/0/44/5). Design: a real payment gateway cannot be rolled back by a database transaction.
