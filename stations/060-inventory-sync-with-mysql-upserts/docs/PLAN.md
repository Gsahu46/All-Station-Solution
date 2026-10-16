# Station 060 plan: Inventory sync with MySQL upserts

**Problem.** Basketo's nightly stock sync looked for each SKU's row and inserted it when none was found. A retried job
inserted the same SKU twice (no unique key). With a unique key and `SELECT ... FOR UPDATE`, two warehouses syncing new
SKUs at the same time deadlocked (MySQL error 1213).

**Endpoint.** `PUT /warehouses/{id}/stock` {items:[{sku, quantity}]}, 1 to 1000 items, SKU `[A-Za-z0-9-]{3,30}`
upper-cased with Locale.ROOT, quantity 0 to 1,000,000 (demo limits). 200 {warehouseId, syncedItems, skusInWarehouse};
SKUs not in the snapshot are left alone. 404 warehouse; 422 the same SKU twice (in any case); 400 malformed;
503 after three deadlocks in a row.

**Write path.** One transaction: `SELECT id FROM warehouses WHERE id = ? FOR UPDATE` (404 if none; one sync per
warehouse at a time), then multi-row `INSERT ... VALUES (...), ... AS incoming ON DUPLICATE KEY UPDATE quantity =
incoming.quantity`, 500 rows per statement. The controller re-runs the whole sync up to 3 times on
PessimisticLockingFailureException (InnoDB deadlock victim), logging each one.

**Database.** stock_levels_warehouse_sku UNIQUE, stock_levels_warehouse_fk, stock_levels_quantity_range CHECK,
stock_levels_sku_shape CHECK (REGEXP_LIKE, case-sensitive).

**Found while building.** (1) The upsert alone was not enough: 10 parallel syncs (5 per warehouse, the same 200 new
SKUs) deadlocked inside InnoDB, about 20 times per full test run, and once a request ran out of its 3 attempts (503).
Locking the warehouse row first brought it to 0 to 1 per run (the remaining ones are between warehouses); the retry
covers those. (2) An upsert is also an insert attempt, so it takes the foreign-key S lock on the warehouse row even
when it only updates: a test meant to show the warehouse lock passed without it, and was removed. (3) Connector/J
reports 1 affected row for an unchanged upsert (it asks for found rows), MySQL itself says 0; an update is 2.
(4) In a Turkish locale, `"milk".toUpperCase()` gives "MİLK", which the SKU CHECK refuses.

**Trap.** `SelectThenInsertTrapTest` on two plain JDBC connections: v1 without a unique key inserts RICE-5KG twice;
v2 with FOR UPDATE on two different warehouses' new SKUs deadlocks (1213) every time, because both take the gap lock
and then both insert into it; the upsert does both without looking first.

**Mutations.** no warehouse lock -> green in 1 of 3 runs (the retry absorbed 20+ deadlocks), red in 2
(parallelSnapshotsOfOneWarehouseLeaveOneWholeSnapshot); no retry -> 3 red (2 contract + the two-warehouse concurrency test, from a real deadlock); no
transaction -> 2; adding instead of setting -> 5; toUpperCase() without Locale.ROOT -> 1; no duplicate check -> 1; no
warehouse check -> 1.

**Review.** adds instead of sets, no duplicate check, no warehouse check (FK violation is a 500), no normalisation.

**Practice.** 1: GET one SKU (normalised path, 404). 2: `?mode=full` zeroes SKUs missing from the snapshot in the same
transaction. 3 (paper): the same sync on PostgreSQL.
