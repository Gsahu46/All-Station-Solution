# Station 008 plan: Saved delivery addresses

**Problem.** Tiffino saves address edits with POST; retries on flaky networks create duplicate "home" entries;
deleting twice shows an error.

**Endpoints.** `/customers/{id}/addresses/{label}`: PUT 201/200 (409 at 10 labels), PATCH (JSON Merge Patch) 200/400/404,
DELETE 204 always, GET 200/404; POST 405 + Allow. `GET /customers/{id}/addresses` lists by label.

**Data.** No database. Customers 42, 43; a map by label per customer (a second PUT replaces). No timestamps, so a
repeated request leaves identical state.

**Trap.** POST for edits. `PostForEditsTrapTest`: retried POST -> 2 addresses; retried PUT -> 1.
Mutation: Locale.ROOT removed from label normalising -> Turkish-locale test red.

**Tests.** Trap, `AddressContractTest`, `AddressReplayTest` (Idempotency type).

**Practice.** 1: ETag + If-Match -> 412 (lost updates). 2: default address as its own idempotent resource.
Design: "addTip" PATCH is not idempotent.
