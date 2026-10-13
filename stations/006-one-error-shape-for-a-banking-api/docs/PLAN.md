# Station 006 plan: One error shape for a banking API

**Problem.** Tijori's beneficiary endpoints each fail differently; the app cannot tell wrong IFSC from service down; one
error leaked the database host and SQL.

**Endpoints.** `POST /beneficiaries` (customers) 201 / 400 invalid-request / 400 unknown-ifsc / 409 duplicate / 503
ifsc-directory-unavailable / 500 internal-error with errorId. `GET /beneficiaries/{id}` 200 / 404 (also other customers').
401 unauthenticated, 403 forbidden from Spring Security in the same RFC 9457 shape.

**Data.** No database. Four IFSC branches (simulated), beneficiaries in memory, HTTP Basic demo users asha, ravi (customers),
meera (viewer).

**Trap.** Messages and stack traces in responses. `LeakyErrorsTrapTest`: naive handler leaks host, SQL, class names;
real API returns errorId only. Found while building: Spring's default type-mismatch detail echoed the path value
(SQL); fixed by overriding handleTypeMismatch (red before, green after).

**Tests.** Trap, `BeneficiaryContractTest`, `BeneficiarySecurityTest` (401, 403, cross-customer, script/SQL not echoed).

**Review.** review/ApiErrors.java + review/BeneficiaryService.java: getMessage in 500, echoed rejected values, outage as
400, 403 for other customers, no type-mismatch override. 7 tests fail.

**Practice.** 1: DELETE with the same ownership rule. 2: X-Request-Id in every problem, including 401. Design: translated errors.
