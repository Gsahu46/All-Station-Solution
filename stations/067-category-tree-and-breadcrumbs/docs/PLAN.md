# Station 067 plan: Category tree and breadcrumbs

**Problem.** Kartwala built "Home > Electronics > Phones > Android" with one query per level (4 for a 4-level
product page), and an admin move that put Electronics under Phones made the loop run forever.

**Endpoints.** `GET /categories/{id}/breadcrumb` 200 {id, path, trail[{id, name, slug}]} root first;
`GET /categories/{id}/descendants` 200 {id, descendants[{id, parentId, name, slug, depth}]} depth first, siblings by
name, the category itself excluded. 404 unknown id, 400 non-numeric.

**Queries.** WITH RECURSIVE up (to the root, ORDER BY hops DESC) and down (SEARCH DEPTH FIRST BY name, id), both
with CYCLE id SET looped USING visited so a loop can never run forever.

**Database.** Adjacency list. categories_parent_fk, categories_not_own_parent, categories_slug_shape,
categories_slug_per_parent UNIQUE NULLS NOT DISTINCT (so only one root "home"), index on parent_id. Trigger
categories_no_cycle (BEFORE INSERT OR UPDATE OF parent_id) walks up from the new parent; pg_advisory_xact_lock makes
moves take turns (not tested here). Demo: 13 categories plus Hobbies with 12 levels.

**Trap.** `QueryPerLevelTrapTest`: old loop 4 queries for Android, 14 for Level 12 (new: 1 statement); on an old copy
without the trigger, the move makes a loop and the old loop runs until the test's own limit (1,000 queries) while the
CYCLE clause stops after 3 rows; the real table refuses the move.

**Found while building.** Without the trigger, the trap test's move really created the loop in the shared table and
two contract tests failed after it: the damage outlives the request that caused it.

**Mutations.** no trigger -> 3; no SEARCH clause -> 1; root last -> 4; including the category itself -> 2; plain
UNIQUE (NULLs distinct) -> 1. Not run: removing CYCLE (on a loop it never ends).

**Practice.** 1: children with hasChildren. 2: move a branch, 409 on a loop. 3 (paper): materialised path, closure
table, ltree.
