# Station 048 plan: Product reviews and ratings

**Problem.** Kartwala's product page ran avg(stars), count(*) over every review on each view (2 million rows for a
bestseller), and nothing stopped one customer posting 40 five-star reviews without having bought the product.

**Endpoints.** `POST /products/{id}/reviews` {customerId, stars 1-5, text 1-2000} 201; 409 already reviewed; 422 no
delivered purchase; 404 product. `GET /products/{id}/reviews?page` 10 per page, newest first, Slice (no count query),
reviewCount from the stored row; page 0-99. `GET /products/{id}/rating` {productId, reviewCount, averageStars (1
decimal, half up; null with no reviews)}.

**Code.** Review @ManyToOne LAZY to Product and Customer; ProductRating stored aggregate; addReview is one atomic JPQL
UPDATE in the same transaction as the insert; unique violation mapped to 409 (two posts at once).

**Database.** reviews_one_per_customer, reviews_stars_range, reviews_text_not_blank, reviews_purchase_fk (composite:
the purchase is this customer's purchase of this product; "delivered" is Java only), product_ratings_totals_consistent.
Index purchases(customer_id, product_id): found when deleting 200,000 test customers took 76 s (each FK check scanned
purchases).

**Tests.** RecomputedAverageTrapTest (50,000 reviews; EXPLAIN ANALYZE rows: old 50,000, stored 1; same 4.1),
ReviewContractTest, ReviewDatabaseTest (constraints, review rolled back when the totals row is missing, 20 buyers at
once all counted, one buyer 10 times at once -> one review). Mutations: no aggregate update -> 7 red; delivered check
dropped -> 1; unique-violation catch dropped -> 1; the exists pre-check dropped -> 0 (the unique index already answers
409; the check only saves a failed insert).

**Practice.** 1: edit a review (delta update, row lock; without the lock the parallel edit test fails). 2: a drift
report comparing stored totals with a recount. Design: when to recompute vs store (caching, materialized views).
