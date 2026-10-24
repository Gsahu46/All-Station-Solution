# Station 107 plan: Partial refund approvals

**Problem.** Kartwala (fictional e-commerce): refunds above ₹5,000 need a second approver. Once, partial refunds added
up to more than the order: several agents refunded the same customer at the same moment, and each one's check of
"what is left" passed before the others were saved.

**Endpoints.** `POST /orders/{id}/refunds {amountPaise, reason}` (AGENT): 201, APPROVED at once up to ₹5,000,
PENDING_APPROVAL above; 409 with remainingPaise when more than is left; 404; 400. `POST /refunds/{id}/approvals
{decision}` (APPROVER): 200; 403 for the person who asked; 409 already decided; 404; 400. `GET /orders/{id}`: total,
reserved, remaining, refunds. HTTP Basic demo users; 401/403 by role.

**Fix.** A domain service. The amount is reserved on the order with one conditional UPDATE (`reserved + amount <= total`),
so concurrent requests queue on the row; pending refunds count. A decision locks the refund row (FOR UPDATE); a
rejection releases the amount. Simulation: an approved refund is a record; no money moves.

**Database.** orders_refunds_within_total (0 <= reserved <= total), refunds_amount_positive, refunds_status,
refunds_second_person (decider is not the asker when approval is needed), refunds_decided_by_someone,
refunds_small_not_pending.

**Trap.** `RefundOverlapTrapTest`: the old Java check (sum, then insert, with a 100 ms provider call between) lets 20
concurrent ₹1,000 refunds on a ₹4,999 order through more than 4 times; the API takes exactly 4.

**Review.** The Java sum check put back ("one query fewer, the same rule").

**Practice.** 1: a note required to reject. 2: two approvers above ₹50,000. 3 (paper): refunds through the payment provider.
