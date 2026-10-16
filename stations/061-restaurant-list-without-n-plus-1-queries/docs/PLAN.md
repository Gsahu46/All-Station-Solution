# Station 061 plan: Restaurant list without N+1 queries

**Problem.** Tiffino's home screen loaded a page of restaurants, then for each one its lazy cuisines and its reviews:
1 + 50 + 50 queries for 50 restaurants.

**Endpoint.** `GET /restaurants?city&page&size` (city `[A-Za-z-]{3,30}`, lower-cased with Locale.ROOT; page 0-1000;
size 1-50, default 20). 200 {city, page, size, restaurants[{id, name, cuisines (sorted), rating {average (1 decimal,
null if none), count}}]} in name order (id tie-break). Known city with nothing on the page: empty list. Unknown
city: 404. Bad parameters: 400.

**Queries.** (1) a page of ids (`select r.id ... order by r.name, r.id` with Pageable: LIMIT/OFFSET in SQL);
(2) `findByIdIn` with `@EntityGraph(attributePaths = "cuisines")` (left join); (3) a DTO projection
`select new RatingSummary(id, avg, count) ... group by`. The city is only looked up when the page is empty.

**Database.** cities_code_shape, restaurants_city_fk, restaurants_name_per_city, restaurant_cuisines_pk + FKs (cascade
from restaurant), reviews_rating_range, reviews_restaurant_fk (cascade). Index restaurants (city_code, name, id).

**Found while building.** (1) Hibernate 7.4 pages a collection fetch join in SQL, through a subquery (seen in the
SQL): the old "HHH000104: applying in memory" pitfall (Hibernate 5) did not happen, and `fail_on_pagination_over_collection_fetch`
did not fire. What remains is that JOIN FETCH is an inner join: a restaurant with no cuisines vanishes from the page.
(2) Spring Data ignores repository interfaces nested in a class (the old repositories had to be top-level files).

**Trap.** `NPlusOneTrapTest`: old screen 101 queries for 50 cards; new 3 for 5, 20 and 50; same cards; JOIN FETCH
page drops a restaurant without cuisines. Query count from Hibernate statistics (tests only).

**Mutations.** no entity graph -> 1 red (query count); inner join fetch -> 1; page order lost -> 2; no 404 -> 1;
no lower-casing -> 1; no rounding -> 2.

**Practice.** 1: cuisine filter (exists subquery, still 3 queries). 2: sort=rating (avg desc nulls last, whitelist).
3 (paper): @BatchSize and caching versus the three-query design.
