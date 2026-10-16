# Station 070 · Product catalog on MongoDB

Working Systems · 0–2 years · Specialisation · E-commerce · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring Data MongoDB · MongoDB 8.0 (\$jsonSchema, wildcard index, aggregation, transactions on a replica set) · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (MongoDB for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Products, sellers, stock and orders are demo data, not Kartwala's. Nothing is sold; an order is a document in a test.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **A catalog that changes weekly**

    Phones, shoes, and now sarees with fabric and length. Each category brings its own attributes; a document store keeps each product as one document, whatever it carries.

2.  **Then: orders too?**

    Someone proposes moving stock and orders to MongoDB as well. An order takes one from stock and writes an order: two documents. A retried request fails halfway, and a phone vanishes from stock with no order for it. Seller names copied into every listing go stale when a seller is renamed.

3.  **The decision**

    The catalog fits a document store well. Stock and orders, with rules across documents and frequent joins, stay in PostgreSQL, or must use transactions everywhere.

Choose the store by the shape of the data and the rules between records, not by fashion.

## What are we building?

`POST /catalog/products` stores a product of any category as one document; `GET /catalog/products?category=phones&attr.ram=8GB` finds them through an index.

## An everyday analogy

A shop's catalogue binder: each product is a page, and a saree page simply has different boxes from a phone page. The binder is perfect for that. The till and the stock book are different: one sale must change both, or neither.

## How it works in 4 steps

1.  **At start**, the app makes sure the collection exists with its validator and indexes.
2.  **A new product** is checked in Java, written as a document, and checked again by MongoDB's validator.
3.  **A search** becomes equality filters on `attributes.<name>`, answered by the wildcard index.
4.  **Several documents that must change together** need a transaction, on a replica set.

Check yourself: a seller is renamed. Their name is copied into 3,000 product documents. What has to happen?

All 3,000 copies must be updated, ideally in one transaction; until then, listings show the old name. Or store only the seller's id and look the name up (`$lookup`) on every read. The trap test shows both.

## What this station is not

- **Not a migration.** PostgreSQL stays; this is an evaluation with working code.
- **No sharding or replicas for scale.** One node, a replica set only so transactions work.
- **No orders API.** Orders appear only in the trap test, to show what goes wrong.

## Key terms

| Term                  | Simple meaning                                                          | Everyday example                                       | In this project             |
|-----------------------|-------------------------------------------------------------------------|--------------------------------------------------------|-----------------------------|
| **Document**          | One record as a nested JSON-like object (BSON).                         | A filled-in form, with any extra pages it needs.       | a product                   |
| **Collection**        | A set of documents; MongoDB's table.                                    | A drawer of forms.                                     | `products`                  |
| **Schema validation** | Rules the server checks on every write.                                 | The clerk refusing a form with a blank price.          | the `$jsonSchema` validator |
| **Wildcard index**    | One index over every key under a path.                                  | One card index for every extra page, whatever it asks. | `attributes.$**`            |
| **Aggregation**       | A pipeline of steps: match, group, join, sort.                          | Sorting the drawer into piles and counting them.       | `$group`, `$lookup`         |
| **Replica set**       | Several MongoDB servers holding the same data; needed for transactions. | A ledger kept in duplicate.                            | one node, `rs0`             |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional marketplace): catalog attributes differ per category and change weekly. The team is evaluating a document database, and must decide what goes in it.

## Acceptance criteria

Demo data: three phones and three shoes, seeded at first start.

1.  **Given** a saree with fabric and length, a category nobody planned, **then** `201`, and it can be searched at once.
2.  **Given** `category=phones&attr.ram=8GB`, **then** the two 8GB phones, by SKU.
3.  **Given** a duplicate SKU, **then** `409`.
4.  **Given** a negative or fractional price, or a query operator as a value or field name, **then** `400`.
5.  **Given** a bad document written with the driver directly, **then** MongoDB refuses it.
6.  **Given** a transaction where one write fails, **then** none of its writes remain.

## Requirements

- The collection has a validator: required fields, types and ranges, checked by the server.
- SKUs are unique (an index); attribute searches use the wildcard index.
- User input never becomes a field name or an operator.
- Multi-document changes use a transaction; data that needs them constantly belongs elsewhere.

## Learning objectives

- Model a catalog as documents with Spring Data MongoDB.
- Add schema validation and indexes to a "schemaless" store.
- Use the aggregation pipeline: `$group` and `$lookup`.
- Decide when a document store fits and when it does not.

# 2 · Build: API contract

## Endpoints

| Method | Path                                         | Purpose                                                                                                        |
|--------|----------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| `POST` | `/catalog/products`                          | `{sku, name, category, sellerId, pricePaise, attributes: {name: text}}`; `201`, Location with the document id. |
| `GET`  | `/catalog/products?category=…&attr.<name>=…` | Products matching every filter, at most 50, by SKU.                                                            |

## Status codes

| Status    | When                                                                                                                                                                                                      |
|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 200 / 201 | Results (possibly none) / created                                                                                                                                                                         |
| 400       | A malformed product (price out of range or fractional, a value that is not text, a bad attribute name); a search with neither category nor filter, or a parameter that is not `category` or `attr.<name>` |
| 409       | The SKU exists                                                                                                                                                                                            |

## Captured examples

Captured with curl from the running app on 16 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a saree

**Why:** a new category with its own attributes, and no schema change.

Request

``` code
POST /catalog/products HTTP/1.1
Content-Type: application/json

{
  "sku": "sr-silk-red",
  "name": "Kanjeevaram Silk",
  "category": "sarees",
  "sellerId": 8,
  "pricePaise": 1250000,
  "attributes": {
    "fabric": "silk",
    "colour": "Red",
    "length_m": "6.3"
  }
}
```

Response

``` code
HTTP/1.1 201 
Location: /catalog/products/6ad247a2b5973ad3b26629b0
Content-Type: application/json

{
  "id": "6ad247a2b5973ad3b26629b0",
  "sku": "SR-SILK-RED",
  "name": "Kanjeevaram Silk",
  "category": "sarees",
  "sellerId": 8,
  "pricePaise": 1250000,
  "attributes": {
    "fabric": "silk",
    "colour": "Red",
    "length_m": "6.3"
  }
}
```

### Case 2: phones with 8GB

**Why:** a category and an attribute filter.

Request

``` code
GET /catalog/products?category=phones&attr.ram=8GB HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 377

[
  {
    "id": "6ad247a1b5973ad3b26629aa",
    "sku": "PH-NOVA-8-128",
    "name": "Nova 5G",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 1899900,
    "attributes": {
      "ram": "8GB",
      "storage": "128GB",
      "colour": "Blue"
    }
  },
  {
    "id": "6ad247a1b5973ad3b26629ab",
    "sku": "PH-NOVA-8-256",
    "name": "Nova 5G",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 2199900,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB",
      "colour": "Blue"
    }
  }
]
```

### Case 3: the same SKU again

**Why:** the unique index: `409`.

Request

``` code
POST /catalog/products HTTP/1.1
Content-Type: application/json

{
  "sku": "sr-silk-red",
  "name": "Kanjeevaram Silk",
  "category": "sarees",
  "sellerId": 8,
  "pricePaise": 1250000,
  "attributes": {
    "fabric": "silk"
  }
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "SKU SR-SILK-RED already exists",
  "instance": "/catalog/products",
  "status": 409,
  "title": "Conflict"
}
```

### Case 4: `{"$gt": ""}` as a value

**Why:** attributes are text: `400`, never a query operator.

Request

``` code
POST /catalog/products HTTP/1.1
Content-Type: application/json

{
  "sku": "sr-x",
  "name": "X",
  "category": "sarees",
  "sellerId": 8,
  "pricePaise": 1250000,
  "attributes": {
    "fabric": {
      "$gt": ""
    }
  }
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/catalog/products",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: `attr.$where`

**Why:** attribute names are checked: `400`.

Request

``` code
GET /catalog/products HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Unknown parameter attr.$where",
  "instance": "/catalog/products",
  "status": 400,
  "title": "Bad Request"
}
```

## What MongoDB says

From `docs/capture.sh`, in `mongosh`: the plan for an attribute search (`docs/captures/explain-attributes.txt`) and the validator refusing a negative price written directly (`docs/captures/validator-refuses.txt`).

``` code
{
  "stage": "FETCH",
  "inputStage": {
    "stage": "IXSCAN",
    "indexName": "products_attributes_wildcard",
    "keyPattern": {
      "$_path": 1,
      "attributes.ram": 1
    }
  }
}
```

``` code
Document failed validation: {"operatorName":"properties","propertiesNotSatisfied":[{"propertyName":"pricePaise","details":[{"operatorName":"minimum","specifiedAs":{"minimum":100},"reason":"comparison failed","consideredValue":-100}]}]}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                     | What happens                                  | Proved by                                       |
|--------------------------------------------------------------------------|-----------------------------------------------|-------------------------------------------------|
| A new category                                                           | Stored and searchable                         | `aNewCategoryNeedsNoSchemaChange`               |
| Category and attributes; cross-category; no match                        | Equality filters                              | `searchByCategoryAndAttributes`                 |
| Duplicate SKU                                                            | `409`                                         | `aDuplicateSkuIs409`                            |
| Negative or fractional price; `$where` as a name; an operator as a value | `400`                                         | `malformedProductsAre400`                       |
| `attr.$where`, a dotted path, an operator as category, nothing           | `400`                                         | `queryOperatorsInParametersAreRefused`          |
| Bad documents written with the driver                                    | Refused by the validator and the unique index | `theValidatorAndTheUniqueIndexHoldWithoutJava`  |
| Three inserts, the third invalid, in a transaction                       | None remain                                   | `aTransactionMakesSeveralDocumentsAllOrNothing` |
| An attribute search                                                      | The wildcard index                            | `attributeSearchesUseTheWildcardIndex`          |

## The trap

Plausible but wrong

Using a document store for data that needs joins and multi-document transactions.

- **Two writes, no transaction.** Placing an order takes one phone from `stock`, then inserts into `orders`. A retried request reuses order number ORD-1, the insert fails, and stock is 4 with no order for the missing phone. In a transaction, the same failure leaves stock at 5.
- **Copies go stale.** Listings carry a copy of the seller's name, the usual document-store habit. After the rename, every listing still says "Meera Footwear". The fresh name needs a `$lookup`, MongoDB's join, on every read.

Neither is impossible in MongoDB; both are work you must remember everywhere, while PostgreSQL gives them by default. The catalog has neither problem, which is why it fits.

While building, each fix was undone once: no validator turned 2 tests red; no unique index 2; no wildcard index 1; no attribute-name check 1.

``` code
package com.kartwala.catalog;

import org.bson.Document;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.aggregation.LookupOperation;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Update;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Written first. The team's plan to move orders and stock into MongoDB too, tried on two small examples: an order
 * that touches two collections, and seller names copied into every listing.
 */
class DocumentStoreTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    @BeforeEach
    void collections() {
        mongo.insert(new Document("_id", "PH-NOVA-8-128").append("onHand", 5), "stock");
        mongo.insert(new Document("_id", "ORD-1").append("sku", "PH-NOVA-8-128").append("quantity", 1), "orders");   // yesterday's order
        mongo.insert(new Document("_id", 8L).append("name", "Meera Footwear"), "sellers");
        for (String sku : List.of("SH-RUN-9-BLK", "SH-OXF-9-BRN", "SH-OXF-10-BRN")) {   // each listing carries a copy of the seller's name
            mongo.insert(new Document("_id", sku).append("seller", new Document("id", 8L).append("name", "Meera Footwear")), "listings");
        }
    }

    @AfterEach
    void dropCollections() {
        for (String c : List.of("stock", "orders", "sellers", "listings")) {
            mongo.dropCollection(c);
        }
    }

    private int onHand() {
        return mongo.findById("PH-NOVA-8-128", Document.class, "stock").getInteger("onHand");
    }

    /** Take one from stock, then record the order: two writes, two collections. */
    private void placeOrder(String orderNo) {
        mongo.updateFirst(new Query(Criteria.where("_id").is("PH-NOVA-8-128").and("onHand").gte(1)), new Update().inc("onHand", -1), "stock");
        mongo.insert(new Document("_id", orderNo).append("sku", "PH-NOVA-8-128").append("quantity", 1), "orders");
    }

    @Test
    void withoutATransactionAFailedOrderStillTakesStock() {
        assertThatThrownBy(() -> placeOrder("ORD-1")).isInstanceOf(DuplicateKeyException.class);   // a retried request reuses the order number
        assertThat(onHand()).isEqualTo(4);   // one phone gone, no order to show for it
    }

    @Test
    void aTransactionPutsTheStockBack() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> placeOrder("ORD-1"))).isInstanceOf(DuplicateKeyException.class);
        assertThat(onHand()).isEqualTo(5);
    }

    @Test
    void copiedSellerNamesGoStaleAndALookupIsTheJoin() {
        mongo.updateFirst(new Query(Criteria.where("_id").is(8L)), new Update().set("name", "Meera Shoes & Sandals"), "sellers");
        assertThat(mongo.findAll(Document.class, "listings")).extracting(d -> d.get("seller", Document.class).getString("name"))
                .containsOnly("Meera Footwear");   // every copy still has the old name, until someone updates all of them
        // The fresh name needs a $lookup: MongoDB's join, written as an aggregation stage, run for every read.
        LookupOperation lookup = Aggregation.lookup("sellers", "seller.id", "_id", "current");
        List<Document> joined = mongo.aggregate(Aggregation.newAggregation(lookup, Aggregation.unwind("current")), "listings", Document.class).getMappedResults();
        assertThat(joined).extracting(d -> d.get("current", Document.class).getString("name")).containsOnly("Meera Shoes & Sandals");
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                                           | Check with      |
|----------|-------------------------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below                    | `java -version` |
| Docker   | Docker Desktop (Windows, macOS) or Docker Engine (Linux), running | `docker info`   |
| Maven    | Not needed: the project ships the Maven wrapper                   |                 |

**macOS / Linux**

``` code
docker compose up -d --wait  # MongoDB 8.0 on localhost:27017, as replica set rs0
./mvnw spring-boot:run       # the API on http://localhost:8080
./mvnw test                  # all 12 tests; starts its own MongoDB container
```

**Windows (PowerShell)**

``` code
docker compose up -d --wait
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Look at the documents and the validator in `mongosh`:

``` code
docker compose exec mongo mongosh kartwala
db.products.find({"attributes.ram": "8GB"}, {sku: 1, attributes: 1})
db.getCollectionInfos({name: "products"})[0].options.validator
db.products.aggregate([{$group: {_id: "$category", products: {$sum: 1}}}])
```

## Troubleshooting

| You see                                                                  | Cause                                                                                     | Fix                                                                                      |
|--------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `Transaction numbers are only allowed on a replica set member or mongos` | A standalone MongoDB; Testcontainers 2.0's `MongoDBContainer` is standalone unless asked. | `.withReplicaSet()` in tests; `--replSet` in compose. Found while building this station. |
| `Invalid bean definition with name 'mongo'`                              | A bean called `mongo` next to Spring Boot's MongoClient bean of that name.                | Name your bean something else. Found while building this station.                        |
| `Document failed validation`                                             | A write breaking the `$jsonSchema`.                                                       | Expected; the error's `errInfo` names the rule.                                          |
| `E11000 duplicate key error`                                             | A second product with the same SKU.                                                       | Answered `409` by the app.                                                               |

## Project layout

``` tree
stations/070-product-catalog-on-mongodb/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/catalog/
│   ├── CatalogController.java   ├── Catalog.java   ├── CatalogSchema.java
│   ├── CatalogProduct.java   └── CatalogApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/kartwala/catalog/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the collection behind it.

#### `src/main/java/com/kartwala/catalog/CatalogController.java`

Does  
Validates products; turns `attr.*` parameters into filters, refusing any name that is not plain lower-case.

Why  
No user text becomes a field path or an operator.

Without it  
`attr.$where` or `{"$gt": ""}` reaching the query.

#### `src/main/java/com/kartwala/catalog/Catalog.java`

Does  
Inserts with `MongoTemplate`; searches with `Criteria` equality filters.

Why  
A duplicate SKU becomes `409`; each filter is a value, never parsed.

Without it  
Queries built from JSON text.

#### `src/main/java/com/kartwala/catalog/CatalogSchema.java`

Does  
Creates the collection with its `$jsonSchema` validator and the three indexes, at every start; seeds the demo data once.

Why  
MongoDB applies the validator to every writer, not only this app.

Without it  
"Schemaless" meaning "anything goes".

- Index creation is idempotent: the same name and keys again do nothing.
- The validator is only applied when this app creates the collection; an existing collection needs `collMod`.

#### `src/main/java/com/kartwala/catalog/CatalogProduct.java`

The document as a Java record.

#### `src/main/java/com/kartwala/catalog/CatalogApplication.java`

Entry point, and the `MongoTransactionManager` Spring Boot does not create by itself.

#### `src/main/resources/application.yaml`

The MongoDB URI (`spring.mongodb.uri` in Spring Boot 4) and whole paise only.

#### `compose.yaml`

MongoDB 8.0 as a one-node replica set; the healthcheck starts it on first run.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                  | Result |
|---------------|-------------------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (empty)      | `CatalogContractTest` (5)   | pass   |
| Every station | Reproduce the failure before the fix                  | `DocumentStoreTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database | `CatalogDatabaseTest` (4)   | pass   |

"Constraints" here are the collection's validator and unique index; "rollback" is a multi-document transaction, on a real replica set.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, MongoDB 8.0 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.catalog.CatalogContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.catalog.DocumentStoreTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.catalog.CatalogDatabaseTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/catalog/DocumentStoreTrapTest.java`

Written first: an order across two collections, and copied names.

#### `src/test/java/com/kartwala/catalog/CatalogDatabaseTest.java`

The validator and unique index with the driver, a transaction, the wildcard index, an aggregation.

#### `src/test/java/com/kartwala/catalog/CatalogContractTest.java`

Both endpoints through HTTP, including operator injection.

#### `src/test/java/com/kartwala/catalog/ApiTest.java`

Shared setup.

#### `src/test/java/com/kartwala/catalog/MongoTestConfig.java`

MongoDB 8.0 in Docker as a replica set, via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/catalog/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ProductByIdChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (12 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## One product by id

Add `GET /catalog/products/{id}`: the product behind the Location header. Not 24 hex digits: `400`; unknown: `404`.

**Done when:** both tests in `ProductByIdChallengeTest` pass.

Hints

- `ObjectId.isValid(id)` before `new ObjectId(id)`, which throws otherwise.
- `mongo.findById` returns `null` when nothing matches.

#### `challenge/ProductByIdChallengeTest.java`

``` code
package com.kartwala.catalog;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /catalog/products/{id} returns one product by the id in its Location header. An id that is not
 * 24 hex digits is 400; a well-formed id nobody has is 404.
 */
class ProductByIdChallengeTest extends ApiTest {

    @Test
    void theLocationHeaderLeadsToTheProduct() throws Exception {
        String location = create(CatalogContractTest.SAREE).andReturn().getResponse().getHeader("Location");
        mvc.perform(get(location)).andExpect(status().isOk()).andExpect(jsonPath("$.sku").value("T-SAREE-SILK-RED"));
    }

    @Test
    void malformedIs400AndUnknownIs404() throws Exception {
        mvc.perform(get("/catalog/products/not-an-id")).andExpect(status().isBadRequest());
        mvc.perform(get("/catalog/products/000000000000000000000000")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Counts per value

Add `GET /catalog/facets?category&facet=ram`: the category's products per value of one attribute, with an aggregation.

**Done when:** the test in `FacetChallengeTest` passes.

Hints

- `Aggregation.match(…category…and("attributes." + facet).exists(true))`, then `Aggregation.group("attributes." + facet).count()`.
- Check the facet name with the same pattern as attribute names: it becomes a field path.

#### `challenge/FacetChallengeTest.java`

``` code
package com.kartwala.catalog;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /catalog/facets?category=phones&facet=ram counts the category's products per value of one
 * attribute, with an aggregation ($match, then $group): {"6GB": 1, "8GB": 2}. Products without it are not counted.
 */
class FacetChallengeTest extends ApiTest {

    @Test
    void countsPerValue() throws Exception {
        mvc.perform(get("/catalog/facets").param("category", "phones").param("facet", "ram")).andExpect(status().isOk())
                .andExpect(jsonPath("$.6GB").value(1)).andExpect(jsonPath("$.8GB").value(2));
        mvc.perform(get("/catalog/facets").param("category", "shoes").param("facet", "material")).andExpect(status().isOk())
                .andExpect(jsonPath("$.leather").value(2)).andExpect(jsonPath("$.mesh").value(1));
        mvc.perform(get("/catalog/facets").param("category", "phones").param("facet", "$where")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## MongoDB, PostgreSQL, or both?

For each of these, choose a store and say why: the product catalog, stock levels, orders and payments, reviews, the search index, sellers. If both stores are used, which is the source of truth for what, and how does a product's price reach an order? Compare with station 068, where the same catalog lives in PostgreSQL jsonb.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: an order across two collections, and copied seller names.
2.  Model a product as one document; keep references (seller id) rather than copies.
3.  Give the collection a validator and indexes, created by the app at start.
4.  Refuse operators and field paths from users; use transactions where documents must change together.

## When a document store fits

| Fits well                                           | Fits badly                                                       |
|-----------------------------------------------------|------------------------------------------------------------------|
| Records read and written whole, like a product page | Records that must change together, like stock and orders         |
| Fields that differ per record and change often      | Data joined in many ways, like reports across sellers and orders |
| Nested data owned by one record                     | Shared data copied into many records, like seller names          |
| Scaling reads and writes across servers             | Strict invariants across records, like "never oversell"          |

## Design alternatives and trade-offs

| Approach                                       | What it costs                                     | Verdict                  |
|------------------------------------------------|---------------------------------------------------|--------------------------|
| Catalog in MongoDB, with validator and indexes | A second database to run.                         | Chosen for the catalog   |
| Orders and stock in MongoDB too                | Transactions everywhere, or inconsistent stock.   | The trap                 |
| Catalog in PostgreSQL jsonb (station 068)      | One database; constraints and joins for the rest. | Often enough             |
| Copies of seller data in each product          | Fast reads; stale copies after changes.           | Only with an update plan |
| References plus `$lookup`                      | Always fresh; a join on every read.               | For data that changes    |

## The collection

| Object                         | What                                                    | Why                                             |
|--------------------------------|---------------------------------------------------------|-------------------------------------------------|
| Validator                      | `$jsonSchema`: required fields, types, ranges, patterns | Rules for every writer.                         |
| `products_sku_unique`          | Unique index on `sku`                                   | One product per SKU.                            |
| `products_category_sku`        | Index on `category, sku`                                | Category pages, in SKU order.                   |
| `products_attributes_wildcard` | Wildcard index on `attributes.$**`                      | Any attribute filter, without an index per key. |

``` code
package com.kartwala.catalog;

import com.mongodb.client.MongoDatabase;
import com.mongodb.client.model.CreateCollectionOptions;
import com.mongodb.client.model.IndexOptions;
import com.mongodb.client.model.ValidationOptions;
import org.bson.Document;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * MongoDB has no migrations here, so the app makes sure, at start, that the collection has its rules: a $jsonSchema
 * validator the server applies to every write, and the indexes. Safe to run on every start.
 */
@Component
@Order(1)
class CatalogSchema implements ApplicationRunner {

    static final String VALIDATOR = """
            {"$jsonSchema": {
              "bsonType": "object",
              "required": ["sku", "name", "category", "sellerId", "pricePaise", "attributes"],
              "properties": {
                "sku": {"bsonType": "string", "pattern": "^[A-Z0-9-]{3,30}$"},
                "name": {"bsonType": "string", "minLength": 1, "maxLength": 120},
                "category": {"bsonType": "string", "pattern": "^[a-z]{2,30}$"},
                "sellerId": {"bsonType": "long"},
                "pricePaise": {"bsonType": "int", "minimum": 100, "maximum": 10000000},
                "attributes": {"bsonType": "object", "maxProperties": 20, "additionalProperties": {"bsonType": "string", "maxLength": 40}}
              }}}""";

    private final MongoTemplate mongo;

    CatalogSchema(MongoTemplate mongo) {
        this.mongo = mongo;
    }

    @Override
    public void run(ApplicationArguments args) {
        MongoDatabase db = mongo.getDb();
        if (!mongo.collectionExists("products")) {
            db.createCollection("products", new CreateCollectionOptions().validationOptions(new ValidationOptions().validator(Document.parse(VALIDATOR))));
        }
        var products = db.getCollection("products");
        products.createIndex(new Document("sku", 1), new IndexOptions().name("products_sku_unique").unique(true));
        products.createIndex(new Document("category", 1).append("sku", 1), new IndexOptions().name("products_category_sku"));
        // A wildcard index: one index over every key inside attributes, whatever keys a category brings.
        products.createIndex(new Document("attributes.$**", 1), new IndexOptions().name("products_attributes_wildcard"));
        if (products.countDocuments() == 0) {
            products.insertMany(List.of(
                    product("PH-NOVA-8-128", "Nova 5G", "phones", 7, 1899900, new Document("ram", "8GB").append("storage", "128GB").append("colour", "Blue")),
                    product("PH-NOVA-8-256", "Nova 5G", "phones", 7, 2199900, new Document("ram", "8GB").append("storage", "256GB").append("colour", "Blue")),
                    product("PH-ZEN-6-128", "Zen Lite", "phones", 7, 1299900, new Document("ram", "6GB").append("storage", "128GB")),
                    product("SH-RUN-9-BLK", "Road Runner", "shoes", 8, 349900, new Document("size", "9").append("colour", "Black").append("material", "mesh")),
                    product("SH-OXF-9-BRN", "Oxford Classic", "shoes", 8, 599900, new Document("size", "9").append("colour", "Brown").append("material", "leather")),
                    product("SH-OXF-10-BRN", "Oxford Classic", "shoes", 8, 599900, new Document("size", "10").append("colour", "Brown").append("material", "leather"))));
        }
    }

    private static Document product(String sku, String name, String category, long seller, int paise, Document attributes) {
        return new Document("sku", sku).append("name", name).append("category", category).append("sellerId", seller)
                .append("pricePaise", paise).append("attributes", attributes);
    }
}
```

# 3 · Go deeper: Production

Replica sets  
Production MongoDB runs as a replica set of at least three members; one node here only enables transactions.

Changing the validator  
Use `collMod` with `validationLevel: moderate` first, so existing documents that break new rules can be fixed before they are enforced.

Two databases  
Keeping MongoDB and PostgreSQL consistent (a product's price reaching an order) needs an outbox or events; nothing spans both stores' transactions.

Licence  
MongoDB Community is under the SSPL; check that it suits how the service is offered.

# 3 · Go deeper: Interview

## Interview takeaways

When would you choose a document database?

When records are read and written whole, vary in shape, and rarely need joins or rules across records; a product catalog is the classic case.

Is MongoDB schemaless?

It does not require a schema, but it supports \$jsonSchema validators that the server enforces on writes; a production collection should have one.

Does MongoDB support transactions?

Yes, multi-document ACID transactions since 4.0, on replica sets (and sharded clusters since 4.2); they have limits and costs, so designs avoid needing them constantly.

Embed or reference?

Embed data owned by the document and read with it; reference data shared by many documents or changed independently, and join with \$lookup or a second query.

What is NoSQL injection?

User input becoming a query operator or field path, such as {"\$gt": ""} or \$where; prevent it by validating types and names and never building queries from JSON text.

## Self-check rubric

| Area        | Meets the bar                  | Above the bar                             |
|-------------|--------------------------------|-------------------------------------------|
| Correctness | All 12 tests pass.             | You ran the explain in mongosh.           |
| MongoDB     | Documents, validator, indexes. | Wildcard index and aggregation.           |
| Safety      | No operator injection.         | Why a replica set is needed.              |
| Judgement   | Catalog in, orders out.        | Embed vs reference, argued for one field. |

# 3 · Go deeper: Review

## No reviewer view for this station

This station has no flawed version to review. Use this checklist when data moves to a document store:

- Which writes touch more than one document, and are they in a transaction?
- What is copied into documents, and who updates every copy?
- Does the collection have a validator and the indexes its queries need?
- Can any request value become a field name or an operator?
