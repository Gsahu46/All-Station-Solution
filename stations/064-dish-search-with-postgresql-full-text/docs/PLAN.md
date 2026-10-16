# Station 064 plan: Dish search with PostgreSQL full-text

**Problem.** Tiffino searched dishes with `name LIKE '%' || q || '%'`: "paneer tikka" missed "Paneer Tikka Masala"
(case), "Masala Dosas" missed "Masala Dosa" (word forms), descriptions were never searched, and a leading wildcard
cannot use a B-tree index.

**Endpoint.** `GET /dishes/search?q&city`: q 2-100 characters (stripped), city lower-cased. 200 {q, city,
dishes[{id, name, restaurant, pricePaise}]} at most 20, by ts_rank desc then id. No match, only stop words, or a
typo: empty list. Bad parameters: 400.

**Database.** `search` tsvector GENERATED ALWAYS ... STORED: name weight A + description weight B, 'english'. GIN
index dishes_search; index on city. Constraints dishes_city_shape, dishes_name_not_blank, dishes_price_range. Demo: 8
dishes by hand + 200,000 generated without paneer/tikka/dosa.

**Query.** websearch_to_tsquery('english', :q) (never a syntax error; "quotes", -word, or).

**Found while building.** (1) Spring wraps grammar errors without the PostgreSQL message: assert on the root cause.
(2) The LIKE query was not a Seq Scan: it used the city index and read every Pune dish; the plan test asserts
"not the GIN index" and pages instead. (3) Ordering by id alone with LIMIT changed the plan (walks the primary key),
which the page test also catches. (4) Challenge 2's trigram index on lower(name) made `lower(name) LIKE '%paneer%'`
indexable (6 pages): the trap test now measures the old query exactly (`name LIKE`).

**Mutations.** to_tsquery -> 6; plainto_tsquery -> 1; 'simple' dictionary -> 3; no GIN -> 1; no rank -> 2; no
lower-casing -> 1; name only in the vector -> 4.

**Practice.** 1: maxPrice. 2: did-you-mean with pg_trgm. 3 (paper): when a search engine is needed.
