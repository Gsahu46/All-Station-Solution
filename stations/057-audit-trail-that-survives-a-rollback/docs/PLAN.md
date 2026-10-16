# Station 057 plan: Audit trail that survives a rollback

**Problem.** Tijori must audit failed transfer attempts. The old code wrote the failure row in its catch block, with
the same JdbcClient, inside the transaction that then rolled back: the row went with it.

**Endpoints.** `POST /transfers` {fromAccountId, toAccountId, amountPaise ₹1 to ₹5 lakh} 201 COMPLETED; 422 insufficient
funds, same account, unknown account; 400 malformed (not an attempt). `GET /audit-events?accountId` oldest first;
404 unknown account; 400 without accountId. Simulated: balances and a record change; no bank network.

**Code.** AuditTrail.record is @Transactional(REQUIRES_NEW): its own transaction on a second connection.
TransferService.transfer (REQUIRED) records TRANSFER_ATTEMPTED first, registers a TransactionSynchronization whose
afterCompletion records TRANSFER_COMPLETED (status committed) or TRANSFER_FAILED with the reason caught in the method,
or "rolled back after the transfer ran" when the caller rolled back. Calls from afterCompletion must be REQUIRES_NEW.

**Database.** accounts_balance_not_negative; transfers_* (FKs, not to self, amount range, attempt unique);
audit_events_event_known, _reason_on_failure, _one_per_attempt, partial unique audit_events_one_outcome (never both
COMPLETED and FAILED). No foreign keys on audit_events: attempts to unknown accounts are recorded too.

**Tests.** AuditRollbackTrapTest (old: no events; new: ATTEMPTED + FAILED, balance unchanged), TransferContractTest,
AuditDatabaseTest (constraints; REQUIRES_NEW survives a caller's rollback, REQUIRED does not; a transfer returned
normally then rolled back by its caller is FAILED, not COMPLETED). Mutations: REQUIRED in AuditTrail -> 4 red;
COMPLETED written inside the method -> 1; reason not captured -> 2.

**Practice.** 1: attemptId on refusals. 2: lockout after 3 failures in 10 minutes, counted from the trail (429).
Design: audit in the same database vs an outbox vs a log pipeline.
