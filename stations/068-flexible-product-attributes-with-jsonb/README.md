# Station 068 · Flexible product attributes with jsonb

Working Systems · 0–2 years · Core · E-commerce · Types: Database

Spring Boot 4.1.1 · Java 25 · JdbcClient · PostgreSQL 17 jsonb · containment (@\>) · GIN jsonb_path_ops · rules as data · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Sellers, categories and products are demo data (60,006 products), not Kartwala's. Nothing is sold.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **140 columns**

    Phones need RAM and storage, shoes need size and colour, sarees need fabric. Each new category added columns that are empty for every other product.

2.  **Everything in JSON**

    The first fix put the whole product in one jsonb column. A seller typed "free" as the price, and every customer's price filter failed. Duplicate SKUs and unknown sellers got in too.

3.  **The fix**

    Columns for what every product has and the rules it needs; jsonb only for what differs per category, checked against that category's rules.

Flexible data still needs rules. Keep the rules close to the data.

## What are we building?

`POST /products` adds a product with its category's attributes, checked; `GET /products?attr.ram=8GB` finds products by any mix of attributes, through an index.

## An everyday analogy

A registration form: printed boxes everyone fills (name, price, seller), and a page of extra questions that depends on what you register: a phone asks for RAM, a shoe for size. The clerk checks the extra page against that type's list.

## How it works in 4 steps

1.  **Check the printed boxes**: SKU, name, price range, seller.
2.  **Load the category's rules** and check the attributes: known names, allowed values, nothing required missing.
3.  **Store** the fixed fields in columns, the attributes as one jsonb object.
4.  **Search** with "the attributes contain these pairs", answered by the GIN index.

Check yourself: should "brand" be a column or an attribute?

If every product has a brand, people filter and sort by it, and brands are their own table you join to, it is a column with a foreign key. If only some categories have it and it is just shown, an attribute is fine. The test is the one in this station: does it need a constraint or a join?

## What this station is not

- **No admin screen for rules.** Rules are rows; Practice 1 reads them.
- **No numeric ranges on attributes.** Values are text; "RAM at least 8GB" needs typed attributes.
- **No document database.** That is station 070.

## Key terms

| Term              | Simple meaning                                                      | Everyday example                         | In this project                   |
|-------------------|---------------------------------------------------------------------|------------------------------------------|-----------------------------------|
| **Attribute**     | A property that only some products have.                            | RAM for a phone, size for a shoe.        | `attributes`                      |
| **jsonb**         | PostgreSQL's binary JSON type: stored parsed, queryable, indexable. | A labelled box of small notes.           | the `attributes` column           |
| **Containment**   | "The document includes all these key-value pairs."                  | "Has RAM 8GB and storage 256GB."         | `attributes @> '{…}'`             |
| **GIN index**     | An index of the keys and values inside each document.               | A card index of every note in every box. | `products_attributes`             |
| **Rules as data** | The allowed attributes of a category live in a table, not in code.  | A form template per product type.        | `attribute_definitions`           |
| **Column**        | A field every row has, with a type, a check and joins.              | The printed boxes on every form.         | `sku`, `price_paise`, `seller_id` |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional marketplace) has a products table with 140 nullable columns, one set per category.

## Acceptance criteria

Demo data: phones need ram and storage (colour optional); shoes need size and colour (material optional).

1.  **Given** a phone with ram, storage and colour, **then** `201` with the attributes stored.
2.  **Given** a shoe of size 13 with ram and no colour, **then** `422` naming each problem.
3.  **Given** an unknown category or seller, **then** `422`; a duplicate SKU, `409`.
4.  **Given** `attr.ram=8GB&attr.storage=256GB`, **then** only products with both.
5.  **Given** an attribute no category has (or not this category), **then** `400`.
6.  **Given** any search, **then** the GIN index is used.

## Requirements

- Price, seller, category and SKU are columns with constraints.
- Attributes are a jsonb *object*, checked against the category's rules before saving.
- A new category or attribute is a row in `attribute_definitions`, not a release.
- Searches use containment, which the GIN index answers.

## Learning objectives

- Store and query jsonb from Java.
- Index jsonb with GIN and know which operators use it.
- Validate per-category attributes from data.
- Decide what is a column and what is an attribute.

# 2 · Build: API contract

## Endpoints

| Method | Path                                       | Purpose                                                                                           |
|--------|--------------------------------------------|---------------------------------------------------------------------------------------------------|
| `POST` | `/products`                                | `{sku, name, category, sellerId, pricePaise, attributes: {name: value}}`; `201` with the product. |
| `GET`  | `/products?category=…&attr.<name>=<value>` | Products whose attributes include every pair; at most 50.                                         |

## Status codes

| Status    | When                                                                                                                                                                                               |
|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 200 / 201 | Results / created                                                                                                                                                                                  |
| 400       | A malformed body (fractional price, empty value, a bad attribute name, attributes not an object); a search with no or more than 10 filters, an unknown attribute or category, or another parameter |
| 409       | The SKU exists                                                                                                                                                                                     |
| 422       | Attributes that break the category's rules; an unknown category or seller                                                                                                                          |

## Captured examples

Captured with curl from the running app on 16 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a phone

**Why:** the attributes fit the phone rules; the SKU is upper-cased.

Request

``` code
POST /products HTTP/1.1
Content-Type: application/json

{
  "sku": "ph-pixel-12-256",
  "name": "Pixel Pro",
  "category": "phones",
  "sellerId": 7,
  "pricePaise": 5999900,
  "attributes": {
    "ram": "12GB",
    "storage": "256GB",
    "colour": "Obsidian"
  }
}
```

Response

``` code
HTTP/1.1 201 
Location: /products/60007
Content-Type: application/json

{
  "id": 60007,
  "sku": "PH-PIXEL-12-256",
  "name": "Pixel Pro",
  "category": "phones",
  "sellerId": 7,
  "pricePaise": 5999900,
  "attributes": {
    "colour": "Obsidian",
    "ram": "12GB",
    "storage": "256GB"
  }
}
```

### Case 2: a shoe that breaks three rules

**Why:** every problem at once, by attribute.

Request

``` code
POST /products HTTP/1.1
Content-Type: application/json

{
  "sku": "sh-odd-13",
  "name": "Odd Shoe",
  "category": "shoes",
  "sellerId": 8,
  "pricePaise": 99900,
  "attributes": {
    "size": "13",
    "ram": "8GB"
  }
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "These attributes do not fit a shoes product",
  "instance": "/products",
  "status": 422,
  "title": "Unprocessable Content",
  "attributes": {
    "colour": "is required",
    "ram": "not an attribute of this category; known: [colour, material, size]",
    "size": "must be one of [6, 7, 8, 9, 10, 11]"
  }
}
```

### Case 3: 8GB and 256GB phones

**Why:** both pairs must be contained.

Request

``` code
GET /products?category=phones&attr.ram=8GB&attr.storage=256GB HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 7361

[
  {
    "id": 2,
    "sku": "PH-NOVA-8-256",
    "name": "Nova 5G",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 2199900,
    "attributes": {
      "colour": "Blue",
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 8,
    "sku": "GEN-2",
    "name": "Generated 2",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100002,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 14,
    "sku": "GEN-8",
    "name": "Generated 8",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100008,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 20,
    "sku": "GEN-14",
    "name": "Generated 14",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100014,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 26,
    "sku": "GEN-20",
    "name": "Generated 20",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100020,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 32,
    "sku": "GEN-26",
    "name": "Generated 26",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100026,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 38,
    "sku": "GEN-32",
    "name": "Generated 32",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100032,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 44,
    "sku": "GEN-38",
    "name": "Generated 38",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100038,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 50,
    "sku": "GEN-44",
    "name": "Generated 44",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100044,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 56,
    "sku": "GEN-50",
    "name": "Generated 50",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100050,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 62,
    "sku": "GEN-56",
    "name": "Generated 56",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100056,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 68,
    "sku": "GEN-62",
    "name": "Generated 62",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100062,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 74,
    "sku": "GEN-68",
    "name": "Generated 68",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100068,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 80,
    "sku": "GEN-74",
    "name": "Generated 74",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100074,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 86,
    "sku": "GEN-80",
    "name": "Generated 80",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100080,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 92,
    "sku": "GEN-86",
    "name": "Generated 86",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100086,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 98,
    "sku": "GEN-92",
    "name": "Generated 92",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100092,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 104,
    "sku": "GEN-98",
    "name": "Generated 98",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100098,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 110,
    "sku": "GEN-104",
    "name": "Generated 104",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100104,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 116,
    "sku": "GEN-110",
    "name": "Generated 110",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100110,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 122,
    "sku": "GEN-116",
    "name": "Generated 116",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100116,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 128,
    "sku": "GEN-122",
    "name": "Generated 122",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100122,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 134,
    "sku": "GEN-128",
    "name": "Generated 128",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100128,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 140,
    "sku": "GEN-134",
    "name": "Generated 134",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100134,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 146,
    "sku": "GEN-140",
    "name": "Generated 140",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100140,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 152,
    "sku": "GEN-146",
    "name": "Generated 146",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100146,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 158,
    "sku": "GEN-152",
    "name": "Generated 152",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100152,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 164,
    "sku": "GEN-158",
    "name": "Generated 158",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100158,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 170,
    "sku": "GEN-164",
    "name": "Generated 164",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100164,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 176,
    "sku": "GEN-170",
    "name": "Generated 170",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100170,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 182,
    "sku": "GEN-176",
    "name": "Generated 176",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100176,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 188,
    "sku": "GEN-182",
    "name": "Generated 182",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100182,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 194,
    "sku": "GEN-188",
    "name": "Generated 188",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100188,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 200,
    "sku": "GEN-194",
    "name": "Generated 194",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100194,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 206,
    "sku": "GEN-200",
    "name": "Generated 200",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100200,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 212,
    "sku": "GEN-206",
    "name": "Generated 206",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100206,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 218,
    "sku": "GEN-212",
    "name": "Generated 212",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100212,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 224,
    "sku": "GEN-218",
    "name": "Generated 218",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100218,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 230,
    "sku": "GEN-224",
    "name": "Generated 224",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100224,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 236,
    "sku": "GEN-230",
    "name": "Generated 230",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100230,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 242,
    "sku": "GEN-236",
    "name": "Generated 236",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100236,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 248,
    "sku": "GEN-242",
    "name": "Generated 242",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100242,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 254,
    "sku": "GEN-248",
    "name": "Generated 248",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100248,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 260,
    "sku": "GEN-254",
    "name": "Generated 254",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100254,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 266,
    "sku": "GEN-260",
    "name": "Generated 260",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100260,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 272,
    "sku": "GEN-266",
    "name": "Generated 266",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100266,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 278,
    "sku": "GEN-272",
    "name": "Generated 272",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100272,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 284,
    "sku": "GEN-278",
    "name": "Generated 278",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100278,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 290,
    "sku": "GEN-284",
    "name": "Generated 284",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100284,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  },
  {
    "id": 296,
    "sku": "GEN-290",
    "name": "Generated 290",
    "category": "phones",
    "sellerId": 7,
    "pricePaise": 100290,
    "attributes": {
      "ram": "8GB",
      "storage": "256GB"
    }
  }
]
```

### Case 4: size 9, leather, any category

**Why:** attributes search across categories that share names.

Request

``` code
GET /products?attr.size=9&attr.material=leather HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 171

[
  {
    "id": 5,
    "sku": "SH-OXF-9-BRN",
    "name": "Oxford Classic",
    "category": "shoes",
    "sellerId": 8,
    "pricePaise": 599900,
    "attributes": {
      "colour": "Brown",
      "material": "leather",
      "size": "9"
    }
  }
]
```

### Case 5: shoes with 8GB RAM

**Why:** `400`: shoes have no ram attribute.

Request

``` code
GET /products?category=shoes&attr.ram=8GB HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "No attribute ram for shoes",
  "instance": "/products",
  "status": 400,
  "title": "Bad Request"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                              | What happens          | Proved by                                      |
|---------------------------------------------------|-----------------------|------------------------------------------------|
| A valid phone                                     | `201`, stored as sent | `aPhoneWithItsOwnAttributesIsCreated`          |
| Unknown, not-allowed and missing attributes       | `422` listing each    | `attributesAreCheckedAgainstTheCategorysRules` |
| Unknown category or seller; duplicate SKU         | `422`; `409`          | `unknownCategorySellerOrADuplicateSku`         |
| Fractional price, empty value, bad name, an array | `400`                 | `malformedBodiesAre400`                        |
| Two filters; a cross-category filter; no match    | Containment           | `searchByAnyMixOfAttributes`                   |
| A filter no category has                          | `400`                 | `searchingForSomethingNoCategoryHasIs400`      |
| An array as attributes; a bad rule; a half upload | Refused; rolled back  | `ProductDatabaseTest`                          |
| Duplicate keys in the JSON                        | The last one wins     | `jsonbStoresTheDocumentNormalised`             |

## The trap

Plausible but wrong

Putting everything in jsonb, including fields that need constraints and joins.

The test builds the old table: one `data` column per product, price and seller inside. Then:

- **Anything gets in.** A second `PH-NOVA-8-128`, a price of `"free"`, seller 999, RAM `"lots"`: all accepted. There is nothing to attach a constraint to.
- **One bad row breaks everyone.** `(data->>'price')::int < 200000` worked, until the "free" row: then it fails for every customer with "invalid input syntax for type integer: "free"".
- **The real table refuses the same rows**: `products_sku_unique`, `products_price_range`, `products_seller_fk`.
- **The index only helps the right operator.** `attributes @> '{"ram": "12GB"}'` uses the GIN index; `attributes->>'ram' = '12GB'` reads every row.

While building, each fix was undone once: without the allowed-values check, the required check, the search's name check, the GIN index, or the "must be an object" CHECK, 1 test turned red each.

``` code
                               QUERY PLAN                               
------------------------------------------------------------------------
 Bitmap Heap Scan on products (actual rows=1 loops=1)
   Recheck Cond: (attributes @> '{"ram": "12GB"}'::jsonb)
   Heap Blocks: exact=1
   ->  Bitmap Index Scan on products_attributes (actual rows=1 loops=1)
         Index Cond: (attributes @> '{"ram": "12GB"}'::jsonb)
(5 rows)
```

``` code
                       QUERY PLAN                        
---------------------------------------------------------
 Seq Scan on products (actual rows=1 loops=1)
   Filter: ((attributes ->> 'ram'::text) = '12GB'::text)
   Rows Removed by Filter: 60006
(3 rows)
```

``` code
package com.kartwala.attributes;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Written first. The old table kept the whole product in one jsonb column, price and seller included, on a copy of
 * the demo catalog. Then the same mistakes against the real table.
 */
class EverythingInJsonbTrapTest extends ApiTest {

    @BeforeEach
    void oldTable() {
        jdbc.sql("CREATE TABLE old_products (id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, data JSONB NOT NULL)").update();
        jdbc.sql("""
                INSERT INTO old_products (data) SELECT jsonb_build_object('sku', sku, 'name', name, 'category', category_code,
                    'seller', seller_id, 'price', price_paise) || attributes FROM products""").update();
    }

    @AfterEach
    void dropOldTable() {
        jdbc.sql("DROP TABLE old_products").update();
    }

    @Test
    void anythingGetsIntoTheOldTable() {
        jdbc.sql("INSERT INTO old_products (data) VALUES ('{\"sku\": \"PH-NOVA-8-128\", \"price\": \"free\", \"seller\": 999, \"ram\": \"lots\"}')").update();
        assertThat(jdbc.sql("SELECT count(*) FROM old_products WHERE data->>'sku' = 'PH-NOVA-8-128'").query(Long.class).single()).isEqualTo(2);   // a duplicate SKU
    }

    @Test
    void oneBadPriceBreaksEveryPriceQuery() {
        String under2000 = "SELECT count(*) FROM old_products WHERE (data->>'price')::int < 200000";
        assertThat(jdbc.sql(under2000).query(Long.class).single()).isPositive();
        jdbc.sql("INSERT INTO old_products (data) VALUES ('{\"sku\": \"T-ODD\", \"price\": \"free\"}')").update();
        assertThatThrownBy(() -> jdbc.sql(under2000).query(Long.class).single()).rootCause()
                .hasMessageContaining("invalid input syntax for type integer: \"free\"");   // every customer's price filter now fails
    }

    @Test
    void theRealTableRefusesTheSameRows() {
        String insert = "INSERT INTO products (sku, name, category_code, seller_id, price_paise, attributes) VALUES (?, 'X', 'phones', ?, ?, '{}')";
        assertThatThrownBy(() -> jdbc.sql(insert).params("PH-NOVA-8-128", 7, 100000).update()).isInstanceOf(DataAccessException.class).hasMessageContaining("products_sku_unique");
        assertThatThrownBy(() -> jdbc.sql(insert).params("T-FREE", 7, 0).update()).hasMessageContaining("products_price_range");
        assertThatThrownBy(() -> jdbc.sql(insert).params("T-NOBODY", 999, 100000).update()).hasMessageContaining("products_seller_fk");
    }

    @Test
    void containmentUsesTheGinIndexTheArrowOperatorDoesNot() {
        assertThat(indexesUsed("SELECT id FROM products WHERE attributes @> CAST(:wanted AS jsonb)", Map.of("wanted", "{\"ram\": \"12GB\"}")))
                .containsExactly("products_attributes");
        assertThat(indexesUsed("SELECT id FROM products WHERE attributes->>'ram' = :ram", Map.of("ram", "12GB"))).isEmpty();
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
docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 13 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

See how jsonb stores what you send:

``` code
docker compose exec postgres psql -U kartwala -d kartwala
SELECT '{"size": "8", "colour": "Red", "colour": "Blue"}'::jsonb;    -- keys reordered, the last duplicate wins
SELECT '{"ram": "8GB", "storage": "128GB"}'::jsonb @> '{"ram": "8GB"}';
SELECT attributes->>'ram', count(*) FROM products WHERE category_code = 'phones' GROUP BY 1;
```

## Troubleshooting

| You see                                                                            | Cause                                                                  | Fix                                                                              |
|------------------------------------------------------------------------------------|------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| `Not allowed to mix named and traditional ? placeholders`                          | The jsonb operators `?`, `?|`, `?&` look like JDBC placeholders.       | Use `jsonb_exists(…)` or `->> … IS NOT NULL`. Found while building this station. |
| `column "attributes" is of type jsonb but expression is of type character varying` | A JSON string bound as text.                                           | `CAST(? AS jsonb)`, as here.                                                     |
| A search that ignores the GIN index                                                | `->>` comparisons; `jsonb_path_ops` only supports `@>` (and jsonpath). | Use containment, or an expression index for one hot key.                         |
| `invalid input syntax for type integer`                                            | A cast of a jsonb value that is not a number.                          | Fields you compute with belong in typed columns.                                 |

## Project layout

``` tree
stations/068-flexible-product-attributes-with-jsonb/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/attributes/
│   ├── ProductController.java   ├── ProductCatalog.java   ├── AttributeRules.java   └── AttributesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__products.sql, V2__demo_products.sql
├── src/test/java/com/kartwala/attributes/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/kartwala/attributes/ProductController.java`

Does  
Validates the body; turns `attr.*` parameters into the wanted pairs.

Why  
Every value is checked for shape and size before the database.

Without it  
A 10 MB attribute value, or an attribute name with SQL in it.

#### `src/main/java/com/kartwala/attributes/ProductCatalog.java`

Does  
Checks attributes against the rules, inserts with `CAST(? AS jsonb)`, searches with `@>`.

Why  
One containment query for any number of filters, through one index.

Without it  
A `->>` comparison per filter, and no index.

- The wanted pairs are written as a JSON object by Jackson and bound as one parameter: no JSON is built by string concatenation.

#### `src/main/java/com/kartwala/attributes/AttributeRules.java`

Does  
Reads a category's rules and lists every problem with a set of attributes.

Why  
Rules are rows, so a new category needs no code.

Without it  
Attributes nobody can search or display consistently.

#### `src/main/resources/db/migration/V1__products.sql`

Does  
Columns with constraints, jsonb with a shape check, the GIN index, and the rules table.

Why  
`jsonb_path_ops` is smaller and faster for `@>`, the one question asked.

Without it  
A table that accepts anything.

#### `src/main/resources/db/migration/V2__demo_products.sql`

Rules for phones and shoes, 6 products by hand and 60,000 generated.

#### `src/main/resources/application.yaml`

Whole paise only.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/kartwala/attributes/AttributesApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                      | Result |
|---------------|-------------------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (empty)      | `ProductContractTest` (6)       | pass   |
| Every station | Reproduce the failure before the fix                  | `EverythingInJsonbTrapTest` (4) | pass   |
| Database      | Rollback and constraint tests against a real database | `ProductDatabaseTest` (3)       | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.attributes.ProductDatabaseTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.attributes.ProductContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.attributes.EverythingInJsonbTrapTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/attributes/EverythingInJsonbTrapTest.java`

Written first: the old one-column table, its failures, and which operator the index helps.

#### `src/test/java/com/kartwala/attributes/ProductDatabaseTest.java`

Named constraints, a rolled-back upload, and how jsonb normalises.

#### `src/test/java/com/kartwala/attributes/ProductContractTest.java`

Both endpoints through HTTP.

#### `src/test/java/com/kartwala/attributes/ApiTest.java`

Shared setup and the plan reader.

#### `src/test/java/com/kartwala/attributes/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/attributes/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=AttributeFormChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (13 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## The seller's form

Add `GET /categories/{code}/attributes`: the category's rules, by name, so a form can be built from data.

**Done when:** the test in `AttributeFormChallengeTest` passes.

Hints

- `AttributeRules.of` already reads them.
- An empty result means the category does not exist: `404`.

#### `challenge/AttributeFormChallengeTest.java`

``` code
package com.kartwala.attributes;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /categories/{code}/attributes lists a category's attribute rules, by name, so the seller's form can
 * be built from data: [{name, required, allowed}], allowed null for free text. Unknown category: 404.
 */
class AttributeFormChallengeTest extends ApiTest {

    @Test
    void theRulesOfACategory() throws Exception {
        mvc.perform(get("/categories/shoes/attributes")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("colour", "material", "size")))
                .andExpect(jsonPath("$[*].required", contains(true, false, true)))
                .andExpect(jsonPath("$[0].allowed").doesNotExist())
                .andExpect(jsonPath("$[1].allowed", contains("leather", "canvas", "mesh")));
        mvc.perform(get("/categories/laptops/attributes")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Counts per value

Add `GET /products/facets?category&facet=ram&attr.*`: products per value of one attribute, among those matching the other filters.

**Done when:** the test in `AttributeFacetChallengeTest` passes.

Hints

- `GROUP BY attributes->>:facet`, filtered with the same containment as the search.
- Do not write `attributes ? :facet`: JDBC reads that `?` as a placeholder. Found while building this station.

#### `challenge/AttributeFacetChallengeTest.java`

``` code
package com.kartwala.attributes;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /products/facets?category=phones&facet=ram&attr.storage=128GB counts the products per value of one
 * attribute, among those matching the other filters: {"6GB": 10001, "8GB": 1}. The facet must be an attribute of the
 * category (else 400).
 */
class AttributeFacetChallengeTest extends ApiTest {

    @Test
    void countsPerValue() throws Exception {
        mvc.perform(get("/products/facets").param("category", "phones").param("facet", "ram")).andExpect(status().isOk())
                .andExpect(jsonPath("$.4GB").value(10000)).andExpect(jsonPath("$.6GB").value(10001)).andExpect(jsonPath("$.8GB").value(10002));
        mvc.perform(get("/products/facets").param("category", "phones").param("facet", "ram").param("attr.storage", "128GB")).andExpect(status().isOk())
                .andExpect(jsonPath("$.6GB").value(10001)).andExpect(jsonPath("$.8GB").value(1)).andExpect(jsonPath("$.4GB").doesNotExist());
        mvc.perform(get("/products/facets").param("category", "phones").param("facet", "size")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Promote an attribute to a column

Product wants "brand" on every product, filterable and sortable, with a brand page that lists the brand's products and a logo from a `brands` table. Write the migration that moves `attributes->>'brand'` into a `brand_id` column: adding it, backfilling in batches, cleaning values that match no brand, adding the foreign key `NOT VALID` then validating it, and removing the key from the jsonb. What does the API look like during the change?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the all-jsonb table and what goes wrong with it.
2.  Split fields: columns for what every product has and needs rules or joins, jsonb for the rest.
3.  Put each category's rules in a table, and check attributes against them before saving.
4.  Search by containment, with a GIN index built for it.

## Column or attribute?

| Question                                      | Yes → column            | No → attribute        |
|-----------------------------------------------|-------------------------|-----------------------|
| Does every product have it?                   | price, seller, SKU      | RAM, size             |
| Does it need a constraint?                    | price range, unique SKU | free text like colour |
| Is it joined to another table?                | seller, category        | storage size          |
| Is it summed, sorted or compared as a number? | price                   | a size shown as text  |

## Design alternatives and trade-offs

| Approach                                                   | What it costs                                            | Verdict                |
|------------------------------------------------------------|----------------------------------------------------------|------------------------|
| Columns for common fields + jsonb attributes + rules table | Validation in the app; text values.                      | Chosen                 |
| One wide table with a column per attribute                 | Hundreds of nullable columns; a migration per category.  | The starting point     |
| Everything in jsonb                                        | No constraints, no joins, fragile casts.                 | The trap               |
| Entity-attribute-value rows (product_id, name, value)      | Flexible; every filter is a self-join; no types.         | Hard to query          |
| A table per category                                       | Typed and constrained; cross-category search is a UNION. | Few, stable categories |
| A document database                                        | Flexible documents; joins and transactions are harder.   | Station 070            |

## Database design

| Object                                                                                      | What                                        | Why                                           |
|---------------------------------------------------------------------------------------------|---------------------------------------------|-----------------------------------------------|
| `products_sku_unique`, `products_price_range`, `products_seller_fk`, `products_category_fk` | Constraints on columns                      | The rules the old table could not hold.       |
| `products_attributes_object`                                                                | CHECK `jsonb_typeof(attributes) = 'object'` | No arrays or strings where an object belongs. |
| `products_attributes`                                                                       | GIN `(attributes jsonb_path_ops)`           | Containment searches.                         |
| `attribute_definitions`                                                                     | PK (category, name), name shape CHECK       | The rules, as data.                           |

``` code
CREATE TABLE sellers (
    id   BIGINT       PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE categories (
    code VARCHAR(30) PRIMARY KEY,
    name VARCHAR(60) NOT NULL
);

-- What each category's attributes may be. Read by the app to validate; data, not code, so a new category needs no release.
CREATE TABLE attribute_definitions (
    category_code VARCHAR(30) NOT NULL CONSTRAINT attribute_definitions_category_fk REFERENCES categories (code),
    name          VARCHAR(30) NOT NULL CONSTRAINT attribute_definitions_name_shape CHECK (name ~ '^[a-z][a-z_]{1,29}$'),
    required      BOOLEAN     NOT NULL,
    allowed       TEXT[],      -- null: any text up to 40 characters
    CONSTRAINT attribute_definitions_pk PRIMARY KEY (category_code, name)
);

-- Fields every product has, that need a rule or a join, are columns. Only what differs per category is jsonb.
CREATE TABLE products (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku           VARCHAR(30)  NOT NULL CONSTRAINT products_sku_unique UNIQUE,
    name          VARCHAR(120) NOT NULL,
    category_code VARCHAR(30)  NOT NULL CONSTRAINT products_category_fk REFERENCES categories (code),
    seller_id     BIGINT       NOT NULL CONSTRAINT products_seller_fk REFERENCES sellers (id),
    price_paise   INTEGER      NOT NULL CONSTRAINT products_price_range CHECK (price_paise BETWEEN 100 AND 10000000),
    attributes    JSONB        NOT NULL CONSTRAINT products_attributes_object CHECK (jsonb_typeof(attributes) = 'object')
);
-- jsonb_path_ops: a smaller GIN index that answers containment (@>) only, which is the one question asked here.
CREATE INDEX products_attributes ON products USING GIN (attributes jsonb_path_ops);
CREATE INDEX products_category ON products (category_code);
```

# 3 · Go deeper: Production

Changing rules  
A new required attribute applies to new products only; existing rows do not change. Decide whether to backfill, or to require it only on edit.

Typos in values  
Free-text attributes drift ("Blue", "blue", "Navy"). Use allowed lists wherever people filter.

Index size  
A GIN index covers every key and value; watch its size and update cost on large, write-heavy tables.

Wide documents  
jsonb values over about 2 kB are compressed and stored out of line (TOAST); keep attributes small.

# 3 · Go deeper: Interview

## Interview takeaways

json or jsonb?

jsonb: stored parsed, so it can be indexed and queried efficiently; json keeps the exact text, including key order and duplicates.

Which jsonb queries can a GIN index answer?

With jsonb_ops: containment (@\>), key existence (?, ?\|, ?&) and jsonpath; with jsonb_path_ops: containment and jsonpath only, with a smaller index.

When should a field be a column instead of jsonb?

When every row has it, it needs a constraint, it is joined, or it is computed with; jsonb cannot carry those rules.

How do you validate jsonb?

In the app, against rules (here a table per category); in the database, at least its shape with CHECK constraints.

What is the risk of casting a jsonb value in a query?

One row with an unexpected value makes the cast fail and the whole query fail for every user.

## Self-check rubric

| Area        | Meets the bar                    | Above the bar                       |
|-------------|----------------------------------|-------------------------------------|
| Correctness | All 13 tests pass.               | You read both saved plans.          |
| jsonb       | Stored, searched with @\>.       | Knows what jsonb_path_ops gives up. |
| Rules       | Attributes checked per category. | Rules as data, not code.            |
| Design      | Price, seller, SKU as columns.   | Can plan promoting an attribute.    |

# 3 · Go deeper: Review

## No reviewer view for this station

This station has no flawed version to review. Use this checklist on any jsonb column:

- Is anything in the jsonb that needs a constraint, a join or arithmetic?
- Is the document checked before it is saved, and its shape checked by the database?
- Do searches use operators the index supports?
- Is any JSON built by string concatenation?
