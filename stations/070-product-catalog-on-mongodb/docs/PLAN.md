# Station 070 plan: Product catalog on MongoDB

**Problem.** Kartwala's catalog attributes differ per category and change weekly; the team is evaluating a document
database, and someone proposed moving orders and stock there too.

**Endpoints.** `POST /catalog/products` {sku (upper-cased), name, category, sellerId, pricePaise, attributes{text}}:
201 + Location /catalog/products/<ObjectId>; duplicate SKU 409; malformed, operators as values or field names 400.
`GET /catalog/products?category&attr.<name>=<value>`: equality on attributes.<name>, names checked against
[a-z][a-z_]{1,29} (no $ or dots), at most 50 by sku; neither category nor attr: 400; no match: [].

**MongoDB.** Collection products with a $jsonSchema validator (required fields, sku pattern, pricePaise int
100..10,000,000, sellerId long, attributes object of strings, max 20), created at start by CatalogSchema with
indexes: products_sku_unique, products_category_sku, products_attributes_wildcard (attributes.$**). Demo seed when
empty. MongoTransactionManager bean (Boot does not configure one). compose: one-node replica set rs0, initiated by its
healthcheck. Tests: Testcontainers MongoDBContainer("mongo:8.0").withReplicaSet().

**Trap.** `DocumentStoreTrapTest`: stock then order in two collections without a transaction: a duplicate order
number leaves stock taken and no order; with a transaction the stock is back; seller names copied into listings go
stale after a rename, and the fresh name needs a $lookup.

**Found while building.** (1) Testcontainers 2.0's MongoDBContainer does not start a replica set unless asked
(withReplicaSet); without it: "Transaction numbers are only allowed on a replica set member or mongos". (2) A test
bean named mongo clashed with Spring Boot's MongoClient bean of that name.

**Mutations.** no validator -> 2; no wildcard index -> 1; no unique index -> 2; no attribute-name check -> 1.

**Practice.** 1: GET by id (ObjectId, 400/404). 2: facet counts with an aggregation. 3 (paper): what belongs in
MongoDB and what in PostgreSQL.
