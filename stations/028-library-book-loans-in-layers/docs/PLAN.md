# Station 028 plan: Library book loans in layers

**Problem.** City Library's loan rules (3 books, no loans with a fine unpaid) live in the web controller and were
copied into the kiosk API. The copies drifted: the kiosk lends a 4th book and ignores fines.

**Endpoints.** `POST /loans` 201; `POST /loans/{id}/return` 200 with any fine; `GET /members/{id}/loans` 200;
`POST /kiosk/checkouts` (card + barcode, the scenario's second entry point) 201. 409 refused with a reason
(LIMIT_REACHED, UNPAID_FINE, BOOK_ON_LOAN, ALREADY_RETURNED); 404 unknown member, book or loan; 400 bad body.

**Data.** No database. Layers: two controllers (no rules), `LoanService` (every rule; constructor injection; Clock),
three repository interfaces with in-memory implementations. One `@RestControllerAdvice` for both controllers.
Demo rules: 14 days, Rs 5 a day late. Service methods synchronized: safe while one instance runs.

**Trap.** `RulesInControllersTrapTest`: the two drifted inline copies disagree; the real web and kiosk give the same
409s. Mutations: kiosk without the service -> 1 red; limit off by one -> 2 red; no fine rule -> 2 red.

**Tests.** Trap, `LoanContractTest` (whole app), `LoanServiceTest` (Mockito, no Spring), `LoanControllerSliceTest`
(@WebMvcTest with the service mocked).

**Practice.** 1: pay a fine. 2: renew a loan. Design: where a rule belongs (entity, service, database).
