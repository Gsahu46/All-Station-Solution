# Station 081 plan: Who changed this price?

**Problem.** A Kartwala seller's TV dropped from ₹54,999 to ₹5,499; the free-text change log could not say who or when.

**Endpoints.** HTTP Basic (demo sellers, an admin, support), stateless. `PUT /products/{id}/price` {pricePaise 100 to
100,000,000, whole numbers}: own products for sellers, any for admins; support 403; another seller's product 404.
`GET /products/{id}/history`: newest first, each entry with revision, changedAt, changedBy, change (ADD/MOD),
pricePaise and previousPricePaise; sellers their own, admins and support any.

**History.** Hibernate Envers: Product is @Audited, a custom revision entity (revisions: id, changed_at_ms,
changed_by) with a RevisionListener that takes the name from the SecurityContext and refuses a change with nobody
signed in. The change and its history rows are one transaction. One change = one revision + one products_aud row.

**Database.** products (price > 0, name length), revisions (changed_by shape), products_aud (PK id+rev, revtype
0/1/2), append-only triggers on both history tables (history_is_append_only; TRUNCATE is the owner's and is not
covered). The import is revision 1, so histories start with the original price.

**Trap.** `FreeTextLogTrapTest`: the old text log has two formats, no product in one line, no dates, and can be
edited; the history answers who and when, ignores a name in the body, and refuses UPDATE/DELETE.

**Found while building.** (1) Jackson turns 5499.99 into the long 5499 by default (ACCEPT_FLOAT_AS_INT): money must
arrive as whole paise, so `spring.jackson.deserialization.accept-float-as-int: false`. (2) Setting the same price
again writes no revision: Hibernate does not flush an unchanged row. (3) Envers validated fine against the
Flyway-made audit tables with ddl-auto validate.

**Mutations.** anonymous changes allowed -> 1; no @Audited -> 10; no append-only trigger -> 1; no ownership check ->
1; floats accepted -> 1; denyAll -> authenticated() -> 1.

**Review.** Name from an X-Changed-By header ("support acts for sellers"), support may change prices: 2 of 19 fail.

**Practice.** 1: history between two instants. 2: price at a moment (Envers query by revision timestamp).
3 (paper): history growth (retention, partitioning, archiving) and approvals for big drops.
