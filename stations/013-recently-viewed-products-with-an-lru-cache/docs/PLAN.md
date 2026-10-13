# Station 013 plan: Recently viewed products with an LRU cache

**Problem.** Kartwala's recently-viewed strip kept every product forever (memory grows), and with two servers each
showed a different history.

**Endpoints.** `POST /users/{id}/recently-viewed` {productId} 200 history; `GET` 200 (empty list for new user); 400.

**Data.** No database. LruMap (LinkedHashMap access order + removeEldestEntry): users (max 10,000) -> products (max 10),
one lock for the whole store, copies returned.

**Trap.** Per-server memory treated as shared. `PerServerCacheTrapTest` starts two real app instances: round robin
splits the history; routing by user keeps it whole (limits stated; shared store in a later station).

**Tests.** Trap, `RecentlyViewedContractTest`, `RecentlyViewedConcurrencyTest` (200 and 1,000 parallel requests on
virtual threads, 60 s timeout), `LruMapTest`.

**Review.** review/LruMap (insertion order, >= off by one), review/RecentlyViewed (ConcurrentHashMap, no lock,
unbounded users). 6 failures. Unlocked reads alone were NOT caught in 5 runs, so not used as a finding.

**Practice.** 1: DELETE a product (204 always). 2: 30-day expiry with an injected Clock. Design: sticky vs Valkey vs phone.
