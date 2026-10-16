# Station 056 plan: Timing and auditing with Spring AOP

**Problem.** Paysetu copy-pasted timing and audit code into 120 service methods; half had none. Replacing it with an
aspect, the team then found methods that still were not audited: self-invoked, final and private ones.

**Endpoints.** `POST /payouts` {merchantId, amountPaise 100..10^8, ifsc, accountNumber 9-18 digits} 201 (audited:
PAYOUT_REQUESTED, SUCCESS or FAILURE, subject = merchant, duration); 422 unknown merchant, not enough balance; 400
malformed (never reaches the audited method). `GET /payouts/{id}` 200/404. `GET /audit-events?action&limit` newest
first. Simulated: a payout record is created; no money moves.

**Code.** @Audited(action, subjectParam); AuditAspect @Around("@annotation(audited)") times, proceeds, writes one
event, rethrows; records only the named parameter (never all arguments: account numbers). @Order(0) wraps the
transaction so failure events survive the rollback; HIGHEST_PRECEDENCE broke argument binding (found while building:
"JoinPointMatch was NOT bound"). PayoutService.request @Transactional: conditional debit, then insert.

**Database.** merchants_balance_not_negative; payouts_merchant_fk, _amount_range, _ifsc_shape, _status_known;
audit_events_outcome_known, _error_on_failure, _duration_not_negative.

**Tests.** ProxyLimitsTrapTest (test-only bean, proxied: outside call audited; self-invoked, final (runs on the proxy,
its field null) and private not), PayoutContractTest, PayoutDatabaseTest (constraints; refused INSERT after the
debit rolls back, the FAILURE event stays). Mutations: no annotation -> 4 red; aspect inside the transaction -> 3;
all arguments recorded -> 5; exception swallowed -> 4.

**Practice.** 1: cancel a payout, audited by annotation only. 2: record the operator from the request (V3).
Design: aspects vs explicit calls vs servlet filters.
