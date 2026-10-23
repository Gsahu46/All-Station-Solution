# Station 091 plan: Bulk shipment creation

**Problem.** Dakroute (fictional courier): sellers create up to 500 shipments in one call. One bad address made the
whole batch fail (one transaction, rolled back) with a 500 and no hint which item.

**Endpoint.** `POST /shipments/bulk` {shipments: [{ref, fromPincode, weightGrams, to: {name, line1, city, pincode,
phone}}]}: 200 with a report {created, failed, results: one per item, in order, with index, ref, status, shipmentId
or errors by field}. The list must hold 1 to 500 items (demo rule) or the call is 400; a body that is not JSON of the
right shape is 400 as a whole. Not 207: that is WebDAV's (RFC 4918), with an XML multistatus body.

**Per item.** Each item is validated on its own (Validator, no @Valid cascade on the list) and inserted in its own
statement (autocommit), so a refusal fails that item only. A ref used before, or twice in the batch, fails that item
(unique constraint); anything else the database refuses is "could not be saved", without SQL details.

**Database.** shipments: ref unique and shaped, PIN codes, Indian mobile number, weight 1 to 50,000 g, address present.

**Trap.** `AllOrNothingTrapTest`: three inserts in one transaction with a five-digit PIN code: nothing saved, a
database message. Through the API: two created, item 1 failed with field to.pincode.

**Found while building.** (1) With one transaction around the loop (the review version), PostgreSQL aborts the
transaction at the first refusal: every later item fails, and at commit the earlier "created" ones are rolled back
while the report still says created (seen: report "created 1", no row). (2) Trimming names changed no test: removed.

**Mutations.** one transaction -> 2; @Valid cascading to items -> 2; no per-item validation -> 2; no duplicate catch
-> 1; no batch limit -> 1; ref not upper-cased -> 2; index off by one -> 3.

**Review.** @Transactional on the batch and a 5,000 limit: 3 of 9 fail.

**Practice.** 1: validateOnly dry run. 2: resubmitting the same file: identical items are "existing".
3 (paper): asynchronous batches for 50,000 items.
