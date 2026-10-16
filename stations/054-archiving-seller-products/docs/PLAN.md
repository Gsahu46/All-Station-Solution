# Station 054 plan: Archiving seller products

**Problem.** Kartwala let sellers delete products. The order_lines foreign key had ON DELETE CASCADE "so delete
would not fail": deleting Assam tea deleted its line from paid order KW-1001, whose total went from ₹897 to ₹199.

**Endpoints.** `DELETE /seller/products/{id}` archives (archived_at set; 204; again 204 with nothing changed); another
seller's or unknown product 404. `GET /seller/products?includeArchived` (default false). X-Seller-Id header (demo,
no login): missing or not a number 400.

**Code.** Product entity with @PrePersist (created = updated) and @PreUpdate (updated) callbacks, micro precision;
archive() keeps the first date, so a second DELETE sends no UPDATE. Derived queries for active vs all.

**Database.** order_lines_product_fk ON DELETE RESTRICT; products_price_positive, products_seller_fk,
products_updated_after_created, products_archived_after_created; partial unique index products_seller_name_active
(seller, lower(name)) WHERE archived_at IS NULL.

**Tests.** HardDeleteTrapTest (old CASCADE tables in a rolled-back transaction: ₹897 -> ₹199; today a DELETE is
refused by order_lines_product_fk; the API archives and the history still joins), SellerProductContractTest,
ProductDatabaseTest (constraints, partial index, callbacks against the rows, rollback). Mutations: CASCADE -> 4 red
(the hard delete went through and took product 1 for later tests too); no @PreUpdate -> 2; archive overwrites the
date -> 1; index without WHERE -> 1; default list unfiltered -> 1.

**Practice.** 1: restore (the partial index can refuse it: 409). 2: purge archived products no order had (RESTRICT
decides). Design: soft delete vs history tables vs Hibernate @SoftDelete.
