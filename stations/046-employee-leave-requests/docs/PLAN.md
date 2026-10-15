# Station 046 plan: Employee leave requests

**Problem.** Teamdesk's approval showed the manager the new balance, saved the request as APPROVED and left the
balance in the database unchanged: the service had no @Transactional, so the entities were detached and
`requests.save(request)` merged only the request (the employee is not cascaded). The same lines ran inside a
transaction elsewhere and saved both, which is why it looked random.

**Endpoints.** `POST /leave-requests` {employeeId, startDate, endDate, reason 1-200} 201 PENDING with working days
(Mon-Fri; holidays not modelled); 400 malformed; 422 end before start, weekend only, span over 42 days, unknown
employee. `POST /leave-requests/{id}/approval` 200 {requestId, status, days, employeeId, balanceDays}; 404, 409 already
decided or changed meanwhile (@Version), 422 not enough leave. `GET /employees/{id}/leave-balance` 200/404.

**Code.** Employee, LeaveRequest (@ManyToOne LAZY, @Version both); LeaveDesk @Transactional, approve() changes both
managed entities and calls no save. Controller maps OptimisticLockingFailureException to 409.

**Database.** employees_balance_not_negative; leave_requests_employee_fk, _dates_ordered, _days_range (1-30),
_days_fit_dates, _status_known.

**Tests.** DetachedEntityTrapTest (old desk: shows 9, database 12; inside a transaction: 9 and 9), LeaveContractTest,
LeaveDatabaseTest (constraints, rollback of both rows, 8 parallel approvals, 6 different approvals in parallel),
LeaveJpaTest (@DataJpaTest: dirty checking, save on managed vs detached, and the old desk passing inside the test
transaction). Mutations: no @Transactional -> 5 red; no @Version on Employee -> 1; no status check -> 2; no balance
check -> 1; no @Version on LeaveRequest -> 0 (the employee's version already catches same-request races; it matters
for the reject challenge).

**Practice.** 1: rejection with a note. 2: cancel approved leave, refund, V3 migration for the new status. Design:
how approvals work across several services without one transaction.
