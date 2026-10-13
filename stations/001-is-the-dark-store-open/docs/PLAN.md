# Station 001 plan: Is the dark store open?

**Problem.** Basketo's app shows "delivering in 10 minutes" for a store that is closed for stock-taking, and the status
API answers an unknown store id with 200 and an empty body, so the app cannot tell "missing" from "fine".

**Endpoint.** `GET /stores/{storeId}/status` → 200 (open: promise; closed: reason, promise null), 400 malformed id
(problem), 404 unknown id (problem), 405 other methods.

**Data.** No database (infra none). Four stores in `StoreDirectory`, looked up with `Optional`.

**Trap.** Returning null → 200 with an empty body. `UnknownStoreTrapTest` reproduces it with a naive controller kept in
the tests, then shows the 404.

**Tests.** `UnknownStoreTrapTest`, `StoreStatusContractTest` (MockMvc). No station types.

**Simulated.** The store list.

**Practice.** 1: case-insensitive ids with Locale.ROOT (Turkish-locale test). 2: `GET /stores?city=` list, empty list
not 404. Design: opening hours across midnight and time zones.
