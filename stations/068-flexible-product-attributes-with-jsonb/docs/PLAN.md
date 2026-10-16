# Station 068 plan: Flexible product attributes with jsonb

**Problem.** Kartwala's products table grew to 140 nullable columns (RAM for phones, size for shoes). The first fix
put everything in one jsonb column, price and seller included: no rules, no joins, and one bad price broke every
price filter.

**Endpoints.** `POST /products` {sku (upper-cased), name, category, sellerId, pricePaise, attributes{name: value}}:
201 + Location; attributes checked against attribute_definitions (unknown, not allowed, missing required) -> 422 with
an `attributes` map of problems; unknown category or seller 422; duplicate SKU 409; malformed 400.
`GET /products?category&attr.<name>=<value>`: 1-10 attr filters, all must match (containment @>); unknown attribute
or category 400; other parameters 400; at most 50 by id.

**Database.** Columns for what every product has and needs rules or joins: sku (unique), category (FK), seller (FK),
price (CHECK). jsonb `attributes` for the rest, CHECK jsonb_typeof = 'object'. GIN (attributes jsonb_path_ops).
attribute_definitions (category, name, required, allowed text[]) with a name shape CHECK.

**Trap.** `EverythingInJsonbTrapTest` on old_products (one jsonb column): a duplicate SKU, price "free" and seller 999
all accepted; then `(data->>'price')::int < 200000` fails for everyone ("invalid input syntax for type integer:
"free""); the real table refuses the same rows; @> uses the GIN index, ->> = does not.

**Found while building.** (1) jsonb normalises: keys sorted by length then bytes, last duplicate key wins.
(2) The jsonb `?` operator collides with JDBC's `?` placeholder ("Not allowed to mix named and traditional ?
placeholders"); the solution uses ->> IS NOT NULL.

**Mutations.** no allowed check -> 1; no required check -> 1; no GIN index -> 1; no search-name check -> 1;
no object CHECK -> 1.

**Practice.** 1: GET /categories/{code}/attributes (the form's rules). 2: facet counts per value.
3 (paper): which attributes to promote to columns.
