# Station 069 plan: Scheduled price changes

**Problem.** Kartwala overwrote a product's price when a scheduled job ran. A Diwali price set for midnight went live
when the job next ran, prices before the change were lost, and two overlapping changes left checkout to pick one.

**Endpoints.** `POST /products/{id}/prices` {pricePaise, from, to?} in shop-local time (Asia/Kolkata, config
shop.zone): 201 with the schedule; from in the past 422; to <= from 400; unknown product 404; price out of range 400.
`GET /products/{id}/price?at` (ISO with offset; default now): {productId, at, pricePaise, validFrom, validTo} in shop
time; 404 for an unknown product or no price then.

**Write path.** One transaction: lock the product row (FOR UPDATE: one schedule change per product at a time), find the
window covering `from`, delete windows inside [from, to), shift a window starting inside to start at `to`, cut the
covering window at `from` and continue it after `to`, insert the new window. An exclusion violation (a concurrent
writer outside this path) is 409.

**Database.** prices [valid_from, valid_to) timestamptz, valid_to NULL = open; prices_window_order,
prices_price_range, prices_product_fk, prices_no_overlap EXCLUDE USING gist (product_id WITH =, tstzrange '[)' WITH
&&) with btree_gist. Times bound as OffsetDateTime UTC.

**Trap.** `OverwrittenPriceTrapTest`: the old table (timestamp without time zone, no constraint) read by a UTC server
shows no sale at 00:30 IST and the sale at 05:30 IST; two overlapping changes both match; the real table refuses the
overlap.

**Mutations.** UTC instead of the shop zone -> 3; no remainder after the window -> 2; no past check -> 1; no exclusion
constraint -> 3; closed end (valid_to >= at) -> 1; no shift of a window starting inside -> 1.

**Practice.** 1: GET the full schedule. 2: cancel a future window, merging equal neighbours. 3 (paper): the price on
an order line, and shops in several time zones.
