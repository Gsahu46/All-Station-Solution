# Station 002 plan: Restaurant menu filters

**Problem.** Tiffino's menu API returns all dishes unsorted; customers want veg, under a budget, cheapest first, a few.

**Endpoint.** `GET /restaurants/{id}/menu?veg&maxPrice&sort&limit` → 200 (dishes, empty list allowed), 400 bad or
out-of-range parameter (problem with `errors` map), 404 unknown restaurant.

**Data.** No database. Two restaurants in `MenuCatalog`, dishes in typed-in order. Prices in paise; `maxPrice` in rupees.

**Trap.** limit before sort. `LimitBeforeSortTrapTest`: naive "cheapest 5" includes a Rs 360 dish; fixed returns the true 5.
Mutation check: moving limit above sorted turned 4 tests red.

**Tests.** `LimitBeforeSortTrapTest`, `MenuContractTest`, `MenuQueryTest` (plain unit). No station types.

**Practice.** 1: `q` name search (Locale.ROOT, strip, @Size 40). 2: `totalMatching` before the limit.
Design: the same in SQL at 14,000 rows; which index.
