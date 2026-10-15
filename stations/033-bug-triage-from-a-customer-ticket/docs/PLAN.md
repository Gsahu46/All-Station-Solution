# Station 033 plan: Bug triage from a customer ticket

**Problem.** Ticket: "refund button does nothing" on KW-1042. The app got a 500 and showed nothing; the only clue is a
stack trace and a request id. Cause: an order without a coupon had a null coupon, and the refund calculator read
`order.coupon().discountPaise()`. Last month a similar ticket was "fixed" with a null check in the part-refund path;
the whole-order path still failed.

**Endpoint.** `POST /refunds` {orderId, lineIds?} 201 {refundId, orderId, lineIds, amountPaise, status RECORDED}
(no lineIds = every line not yet refunded); 404 order; 422 unknown line; 409 already refunded; 400 bad body;
500 problem with requestId for anything unexpected. A refund record is created; no payment provider is called.

**Fix.** At the cause: `Order`'s compact constructor turns a null coupon into `Coupon.NONE`. Coupon share is
proportional to price, rounded down; the refund that empties the order gets paid minus already refunded.
`UnexpectedErrorHandler` (extends ResponseEntityExceptionHandler) logs unexpected errors at ERROR with the stack trace
while the request id is in the MDC, counts `refunds.requests{outcome=failed}`, and returns the id in the body.

**Trap.** `NullCouponTrapTest`: the ticket's request throws the helpful NPE on the old code (top frame couponShare);
the old patch fixes the part path only; the model fix covers every path. `TicketReplay` (test sources) prints the real
stack trace for the page. Mutations: null coupon kept -> 7 red; no error log -> 1; no remainder rule -> 2; no
requestId in body -> 1. Not extending ResponseEntityExceptionHandler was not caught (Boot's own advice handles 4xx
first); kept for order-independence, not claimed.

**Operations.** Metric `refunds.requests{outcome}`, alert on failed, rollback, runbook from request id to stack trace,
failure drill (`kartwala.refunds.simulate-ledger-failure`), `OperationsDrillTest`.

**Practice.** 1: second ticket, `/ by zero` on a free order (failing test given). 2: requestId on every problem.
Design: a triage template for the support team.
