# Station 009 plan: Wishlist without duplicates

**Problem.** Kartwala wishlists hold the same phone three times: SKUs arrive as "ph-12", "PH-12", " PH-12 ", and the
SKU class overrode equals without hashCode.

**Endpoints.** `GET /wishlists/{id}` 200/404; `POST /wishlists/{id}/items` 201 added / 200 already there / 400 bad SKU /
422 unknown product / 404; `DELETE /wishlists/{id}/items/{sku}` 204 always (404 unknown wishlist).

**Data.** No database. `record Sku` normalises (strip, upper, Locale.ROOT) and validates in its constructor; wishlists
are LinkedHashSet<Sku>; catalogue is Map<Sku, Product>.

**Trap.** equals without hashCode, and a mutable key. `EqualsWithoutHashCodeTrapTest`: 3 phones in a HashSet; a mutated
key lost; real API keeps 1. Mutation: no upper-casing in Sku -> 7 tests red.

**Tests.** Trap, `WishlistContractTest`, `SkuTest` (contract pairwise, HashSet/HashMap, Turkish locale).

**Practice.** 1: merge guest wishlist, all or nothing. 2: most-wished counts in HashMap<Sku, Integer>. Design: one
product under two SKUs.
