# Station 065 plan: Seller catalog pages

**Problem.** Kartwala sellers with tens of thousands of products page through their catalog sorted by price. Many
products share a price; the query sorted by price alone, so PostgreSQL ordered ties differently from page to page:
products repeated and others were never shown.

**Endpoint.** `GET /seller/products?page&size&sort` with `X-Seller-Id` (demo: a header instead of a login). Spring
Data Pageable; @PageableDefault(size = 20, sort = "name"); max-page-size 100 (silently capped); sort whitelist name,
pricePaise, createdOn (else 400); id appended as the tie-breaker. Response PagedModel (serialization-mode via-dto):
{content[{id, name, pricePaise, createdOn}], page{size, number, totalElements, totalPages}}. Unknown seller 404,
missing/bad header 400, page past the end: empty content.

**Database.** products_seller_fk, products_name_not_blank, products_price_range, products_name_per_seller; indexes
(seller_id, price_paise, id), (seller_id, created_on, id). Demo: seller 7 with 2,000 products at 10 prices, seller 8
with 30.

**Found while building.** (1) The probe: 100 pages of 20 sorted by price only showed 2,000 rows but 1,616 different
products. (2) @PageableDefault(sort = "name") silently reset the page size to 10, overriding
spring.data.web.pageable.default-page-size. (3) The serialization-mode property lives under spring.data.web.pageable.
(4) A Page here costs 3 queries (seller check, rows, count); a Slice 1. (5) The bug depends on the plan: with
statistics PostgreSQL read the (seller_id, price_paise, id) index and price alone came out stable by luck; without
them it sorted (top-N heapsort) and lost 384 products. The trap test switches index scans off in its transaction.

**Mutations.** no tie-breaker -> 2; no whitelist -> 1; no seller check -> 2; no max-page-size -> 1; default size 10
-> 2.

**Practice.** 1: a Slice feed for infinite scroll (no count). 2: which page a product is on (count rows before it).
3 (paper): totals on 80,000 products.
