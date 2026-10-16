# Station 062 plan: Shipment search by phone number

**Problem.** Dakroute support searches shipments by phone and dates. Phones were stored as typed (+91 98765 43210,
098765..., 98765...), the search cleaned them in SQL with regexp_replace, and the index someone added on phone was
never used: a sequential scan of every shipment.

**Endpoint.** `GET /shipments/search?phone&from&to`. Phone normalised in Java to 10 digits ([6-9]\d{9}; strips spaces,
dashes, brackets, +91, a leading 0). ISO dates, forwards, at most 366 days (demo rule). 200 {phone, from, to,
shipments[{awb, bookedOn, status}]} newest first (booked_on desc, id desc), at most 50. No match: empty list. Bad
phone / dates / missing parameter: 400.

**Database.** shipments_phone_shape (10 digits only, so the column is compared as stored), shipments_awb_unique,
shipments_awb_shape, shipments_status_known. V3: index shipments_phone_booked_on (phone, booked_on), equality first.
Demo data: 3 hand rows for 9876543210 + 300,000 generated (90,000 customers x 3, one seller 9123456789 x 30,000),
January to September 2026.

**Measured (tests, EXPLAIN ANALYZE BUFFERS, no parallel workers).** Old search on a typed-phone copy: Seq Scan,
>100x the pages of the new search (new <= 10 pages). Copy table: no index -> Seq Scan; (phone) only for the seller's
week: 30,000 index entries, >2x the pages of (phone, booked_on) which reads < 300 entries; (booked_on, phone) for a
customer's 9 months: >10x the pages. WAL records for 1000 inserts: ~1000 bare, >3x with 3 indexes.

**Found while building.** (1) `g * 7 % 273` gave only multiples of 7 (273 = 3 x 7 x 13): 39 dates; 11 instead.
(2) VARCHAR(10) rejects a 15-character phone before the CHECK can name itself. (3) For one phone with few heap
pages the (phone) index is only ~2.7x worse in pages, though it reads 30,000 entries; the date-first index returned 3
entries but touched 1,064 pages. (4) A stale target/classes kept a deleted migration and made a challenge test pass.

**Mutations.** no index -> 1; date-first index -> 1; no +91 handling -> 1; no LIMIT -> 2; oldest first -> 2;
no range check -> 1.

**Practice.** 1: GET /shipments/{awb} (unique index, 404/400). 2: status summary from an Index Only Scan (INCLUDE
(status), same index name). 3 (paper): last-4-digits search.
