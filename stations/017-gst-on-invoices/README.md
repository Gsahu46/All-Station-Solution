# Station 017 · GST on invoices

Foundations · 0–1 years · Core · B2B SaaS · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · BigDecimal · enums with data · TreeMap · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** A tax preview only: nothing is stored, no invoice number is issued and nothing is filed with the GST portal. The rates are demo configuration modelled on how Indian GST rates are structured, not a tax reference and not tax advice.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **Billora sends an invoice to an office in Bengaluru**

    It charges IGST at 18% on everything, T-shirts included. The office is in Karnataka, like Billora: it should have been CGST and SGST, and the T-shirts are 5%.

2.  **The CA compares the totals**

    Even with the right rates, Billora's tax is 2 paise more than the CA's, because Billora rounds tax on each line and the CA works it out per rate on the invoice's total.

3.  **The fix**

    Decide the tax type from the seller's state and the place of supply. Look rates up by HSN code, date and price from configuration. Add up the taxable value per rate and round the tax once.

Which tax depends on where; how much depends on what, when and for how much. None of it belongs hard-coded.

## What are we building?

`POST /invoices/tax-preview` takes an invoice date, the place of supply and the lines. It returns each line's rate, a rate-wise tax summary (CGST and SGST, or IGST) and the invoice total. Nothing is stored.

## An everyday analogy

A school canteen bill: tea and samosas are added up first, then the GST on each is worked out once on its subtotal. Nobody works out the tax on each cup of tea separately and adds the rounded paise.

## How it works in 4 steps

1.  **Where**: same state as the seller means CGST + SGST; another state means IGST.
2.  **What, when and how much**: find each line's rate by HSN code, invoice date and price per piece.
3.  **Group by rate**: add up the taxable value of all lines at 5%, all at 18%, and so on.
4.  **Tax once per rate**, rounded to the paisa, then the invoice total.

Check yourself: an 18% sale within a state is 9% CGST + 9% SGST. Is the total tax always the same as 18% IGST?

Almost. Each half is rounded on its own, so it can differ by a paisa: the office invoice below is ₹551.42 within Karnataka and ₹551.40 to Maharashtra.

## What this station is not

- **Not a tax reference.** The rates are demo configuration. Check the current CBIC rate notifications before using any number.
- **No e-invoice, no filing.** Nothing goes to the GST portal; no invoice number is issued.
- **Not every rule.** Services, exports, reverse charge, cess and union territories (challenge 2) are left out.

## Key terms

| Term                | Simple meaning                                                                         | Everyday example                                                   | In this project               |
|---------------------|----------------------------------------------------------------------------------------|--------------------------------------------------------------------|-------------------------------|
| **GST**             | India's tax on the supply of goods and services, added to the price on the invoice.    | 18% on a ₹1,000 keyboard: ₹180 of tax.                             | `totalTaxPaise`               |
| **CGST + SGST**     | Within one state, the tax is split in two halves: one to the Centre, one to the state. | 9% + 9% for a Bengaluru shop selling to a Bengaluru office.        | `cgstPaise`, `sgstPaise`      |
| **IGST**            | Between states, the whole tax is one integrated tax.                                   | 18% IGST for the same shop selling to Mumbai.                      | `igstPaise`                   |
| **Place of supply** | Where the supply is taxed. For goods, usually where they are delivered.                | Delivered to Pune: Maharashtra, code 27.                           | `placeOfSupply`               |
| **HSN code**        | The number that classifies goods; the rate depends on it.                              | 6109 for T-shirts, 8471 for computers and keyboards.               | `hsn` on each line            |
| **Slab**            | A rate that applies from one price up to the next.                                     | T-shirts: 5% up to ₹2,500 a piece, 18% above (demo configuration). | `slabs` in `application.yaml` |

# 2 · Build: Spec

## Business problem

**Billora** (a fictional invoicing app for small sellers in Karnataka) charges IGST at a hard-coded 18% on every line. Buyers in Karnataka get the wrong tax type, T-shirts get the wrong rate, and a rate change means a release. Tax is rounded line by line, so the totals never match the CA's rate-wise working.

## Acceptance criteria

1.  **Given** the office invoice to a buyer in Karnataka (code 29), **then** CGST ₹275.71 and SGST ₹275.71, no IGST.
2.  **Given** the same invoice to Maharashtra (27), **then** IGST ₹551.40, no CGST or SGST.
3.  **Given** an air conditioner invoiced on 21 Sep 2025, **then** 28%; on 22 Sep 2025, 18% (demo configuration).
4.  **Given** a T-shirt at ₹2,500 a piece, **then** 5%; at ₹2,500.01, 18%.
5.  **Given** an HSN code with no rate on the invoice date, **then** `422` naming the line.
6.  **Given** an unknown state code, a wrong HSN format, no lines or a fraction of a quantity, **then** `400`.

## Requirements

- Amounts are whole paise. Tax is computed per rate on the summed taxable value and rounded half up to the paisa, once.
- Within one state each half of the rate is computed and rounded separately; CGST always equals SGST.
- Rates live in configuration: per HSN heading, dated sets of price slabs. A change is a new set, added ahead of time.
- Demo rules: 4-digit HSN headings; 1 to 100 lines; quantity up to 10,000; at most ₹10 lakh a piece.

## Learning objectives

- Choose CGST + SGST or IGST from the seller's state and the place of supply.
- Model states as an enum that carries data (code and name).
- Look up a dated, slabbed rate with two `TreeMap.floorEntry` calls.
- Explain why rounding per line and rounding per invoice give different totals.

# 2 · Build: API contract

## Endpoint

| Method | Path                    | Purpose                                                                               |
|--------|-------------------------|---------------------------------------------------------------------------------------|
| `POST` | `/invoices/tax-preview` | Lines with their rates, a rate-wise tax summary and totals. `200`; nothing is stored. |

## Request body

| Field           | Rule                                                                                                                                         |
|-----------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| `invoiceDate`   | Required, `YYYY-MM-DD`. Picks the rates.                                                                                                     |
| `placeOfSupply` | Two-digit GST state code, as on an e-invoice: `29` Karnataka, `27` Maharashtra, and so on.                                                   |
| `lines`         | 1 to 100, each with `description` (up to 80 characters), `hsn` (4 digits), `quantity` (1 to 10,000) and `unitPricePaise` (1 to 100,000,000). |

## Status codes

| Status | When                                                                         |
|--------|------------------------------------------------------------------------------|
| 200    | Preview computed                                                             |
| 400    | A field is missing, malformed or out of range, or the state code is unknown  |
| 422    | No rate for a line's HSN code on the invoice date; the detail names the line |

## Captured examples

Captured with curl from the running app on 14 Oct 2026, in this order. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the office invoice, Karnataka to Karnataka

**Why:** same state, so each rate is split into CGST and SGST. The 5% lines are added up first (₹2,397 at 2.5% = ₹59.925, rounded to ₹59.93), then the 18% lines (₹2,397.50 at 9% = ₹215.775, rounded to ₹215.78).

Request

``` code
POST /invoices/tax-preview HTTP/1.1
Content-Type: application/json

{
  "invoiceDate": "2026-10-13",
  "placeOfSupply": "29",
  "lines": [
    {
      "description": "Team T-shirt",
      "hsn": "6109",
      "quantity": 3,
      "unitPricePaise": 79900
    },
    {
      "description": "Keyboard",
      "hsn": "8471",
      "quantity": 1,
      "unitPricePaise": 124950
    },
    {
      "description": "Mouse",
      "hsn": "8471",
      "quantity": 1,
      "unitPricePaise": 54950
    },
    {
      "description": "USB cable",
      "hsn": "8544",
      "quantity": 3,
      "unitPricePaise": 19950
    }
  ]
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 971

{
  "invoiceDate": "2026-10-13",
  "sellerState": "29-Karnataka",
  "placeOfSupply": "29-Karnataka",
  "supplyType": "INTRA_STATE",
  "lines": [
    {
      "line": 1,
      "description": "Team T-shirt",
      "hsn": "6109",
      "quantity": 3,
      "unitPricePaise": 79900,
      "taxableValuePaise": 239700,
      "ratePercent": 5
    },
    {
      "line": 2,
      "description": "Keyboard",
      "hsn": "8471",
      "quantity": 1,
      "unitPricePaise": 124950,
      "taxableValuePaise": 124950,
      "ratePercent": 18
    },
    {
      "line": 3,
      "description": "Mouse",
      "hsn": "8471",
      "quantity": 1,
      "unitPricePaise": 54950,
      "taxableValuePaise": 54950,
      "ratePercent": 18
    },
    {
      "line": 4,
      "description": "USB cable",
      "hsn": "8544",
      "quantity": 3,
      "unitPricePaise": 19950,
      "taxableValuePaise": 59850,
      "ratePercent": 18
    }
  ],
  "taxSummary": [
    {
      "ratePercent": 5,
      "taxableValuePaise": 239700,
      "cgstPaise": 5993,
      "sgstPaise": 5993,
      "igstPaise": 0
    },
    {
      "ratePercent": 18,
      "taxableValuePaise": 239750,
      "cgstPaise": 21578,
      "sgstPaise": 21578,
      "igstPaise": 0
    }
  ],
  "taxableValuePaise": 479450,
  "cgstPaise": 27571,
  "sgstPaise": 27571,
  "igstPaise": 0,
  "totalTaxPaise": 55142,
  "invoiceTotalPaise": 534592
}
```

### Case 2: the same invoice to Maharashtra

**Why:** another state, so IGST at the full rate. It is 2 paise less than case 1: one rounding per rate instead of two.

Request

``` code
POST /invoices/tax-preview HTTP/1.1
Content-Type: application/json

{
  "invoiceDate": "2026-10-13",
  "placeOfSupply": "27",
  "lines": [
    {
      "description": "Team T-shirt",
      "hsn": "6109",
      "quantity": 3,
      "unitPricePaise": 79900
    },
    {
      "description": "Keyboard",
      "hsn": "8471",
      "quantity": 1,
      "unitPricePaise": 124950
    },
    {
      "description": "Mouse",
      "hsn": "8471",
      "quantity": 1,
      "unitPricePaise": 54950
    },
    {
      "description": "USB cable",
      "hsn": "8544",
      "quantity": 3,
      "unitPricePaise": 19950
    }
  ]
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 963

{
  "invoiceDate": "2026-10-13",
  "sellerState": "29-Karnataka",
  "placeOfSupply": "27-Maharashtra",
  "supplyType": "INTER_STATE",
  "lines": [
    {
      "line": 1,
      "description": "Team T-shirt",
      "hsn": "6109",
      "quantity": 3,
      "unitPricePaise": 79900,
      "taxableValuePaise": 239700,
      "ratePercent": 5
    },
    {
      "line": 2,
      "description": "Keyboard",
      "hsn": "8471",
      "quantity": 1,
      "unitPricePaise": 124950,
      "taxableValuePaise": 124950,
      "ratePercent": 18
    },
    {
      "line": 3,
      "description": "Mouse",
      "hsn": "8471",
      "quantity": 1,
      "unitPricePaise": 54950,
      "taxableValuePaise": 54950,
      "ratePercent": 18
    },
    {
      "line": 4,
      "description": "USB cable",
      "hsn": "8544",
      "quantity": 3,
      "unitPricePaise": 19950,
      "taxableValuePaise": 59850,
      "ratePercent": 18
    }
  ],
  "taxSummary": [
    {
      "ratePercent": 5,
      "taxableValuePaise": 239700,
      "cgstPaise": 0,
      "sgstPaise": 0,
      "igstPaise": 11985
    },
    {
      "ratePercent": 18,
      "taxableValuePaise": 239750,
      "cgstPaise": 0,
      "sgstPaise": 0,
      "igstPaise": 43155
    }
  ],
  "taxableValuePaise": 479450,
  "cgstPaise": 0,
  "sgstPaise": 0,
  "igstPaise": 55140,
  "totalTaxPaise": 55140,
  "invoiceTotalPaise": 534590
}
```

### Case 3: a ₹1,499 T-shirt on 21 Sep 2025

**Why:** the rate set valid that day taxes T-shirts above ₹1,000 a piece at 12% (demo configuration).

Request

``` code
POST /invoices/tax-preview HTTP/1.1
Content-Type: application/json

{
  "invoiceDate": "2025-09-21",
  "placeOfSupply": "29",
  "lines": [
    {
      "description": "Polo T-shirt",
      "hsn": "6109",
      "quantity": 1,
      "unitPricePaise": 149900
    }
  ]
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 492

{
  "invoiceDate": "2025-09-21",
  "sellerState": "29-Karnataka",
  "placeOfSupply": "29-Karnataka",
  "supplyType": "INTRA_STATE",
  "lines": [
    {
      "line": 1,
      "description": "Polo T-shirt",
      "hsn": "6109",
      "quantity": 1,
      "unitPricePaise": 149900,
      "taxableValuePaise": 149900,
      "ratePercent": 12
    }
  ],
  "taxSummary": [
    {
      "ratePercent": 12,
      "taxableValuePaise": 149900,
      "cgstPaise": 8994,
      "sgstPaise": 8994,
      "igstPaise": 0
    }
  ],
  "taxableValuePaise": 149900,
  "cgstPaise": 8994,
  "sgstPaise": 8994,
  "igstPaise": 0,
  "totalTaxPaise": 17988,
  "invoiceTotalPaise": 167888
}
```

### Case 4: the same T-shirt a day later

**Why:** a new rate set starts on 22 Sep 2025 with the slab at ₹2,500, so ₹1,499 is 5%. Only configuration changed.

Request

``` code
POST /invoices/tax-preview HTTP/1.1
Content-Type: application/json

{
  "invoiceDate": "2025-09-22",
  "placeOfSupply": "29",
  "lines": [
    {
      "description": "Polo T-shirt",
      "hsn": "6109",
      "quantity": 1,
      "unitPricePaise": 149900
    }
  ]
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 489

{
  "invoiceDate": "2025-09-22",
  "sellerState": "29-Karnataka",
  "placeOfSupply": "29-Karnataka",
  "supplyType": "INTRA_STATE",
  "lines": [
    {
      "line": 1,
      "description": "Polo T-shirt",
      "hsn": "6109",
      "quantity": 1,
      "unitPricePaise": 149900,
      "taxableValuePaise": 149900,
      "ratePercent": 5
    }
  ],
  "taxSummary": [
    {
      "ratePercent": 5,
      "taxableValuePaise": 149900,
      "cgstPaise": 3748,
      "sgstPaise": 3748,
      "igstPaise": 0
    }
  ],
  "taxableValuePaise": 149900,
  "cgstPaise": 3748,
  "sgstPaise": 3748,
  "igstPaise": 0,
  "totalTaxPaise": 7496,
  "invoiceTotalPaise": 157396
}
```

### Case 5: an HSN code with no rate

**Why:** no rate is guessed: `422`, naming the line.

Request

``` code
POST /invoices/tax-preview HTTP/1.1
Content-Type: application/json

{
  "invoiceDate": "2026-10-13",
  "placeOfSupply": "29",
  "lines": [
    {
      "description": "Mystery box",
      "hsn": "1234",
      "quantity": 1,
      "unitPricePaise": 10000
    }
  ]
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Line 1: no GST rate for HSN 1234 on 2026-10-13.",
  "instance": "/invoices/tax-preview",
  "status": 422,
  "title": "No GST rate"
}
```

### Case 6: state code 99

**Why:** not a state in this demo: `400`.

Request

``` code
POST /invoices/tax-preview HTTP/1.1
Content-Type: application/json

{
  "invoiceDate": "2026-10-13",
  "placeOfSupply": "99",
  "lines": [
    {
      "description": "Polo T-shirt",
      "hsn": "6109",
      "quantity": 1,
      "unitPricePaise": 149900
    }
  ]
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "No state in this demo has GST state code 99.",
  "instance": "/invoices/tax-preview",
  "status": 400,
  "title": "Unknown state code"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                                  | What happens                                                                      | Proved by                                         |
|---------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|---------------------------------------------------|
| Seller and buyer in Karnataka                                                         | CGST = SGST, per rate                                                             | `aSameStateInvoiceHasCgstAndSgstPerRate`          |
| Buyer in Maharashtra                                                                  | IGST only                                                                         | `anotherStateGetsIgstOnly`                        |
| AC on 21 and 22 Sep 2025                                                              | 28%, then 18%                                                                     | `theRateIsTheOneValidOnTheInvoiceDate`            |
| T-shirt at ₹1,000 / ₹1,000.01 (old set); ₹2,500 / ₹2,500.01 (new set)                 | 5 / 12; 5 / 18                                                                    | `tShirtSlabsByPricePerPieceAndDate`               |
| 30 Jun 2017 (before GST); an unknown heading                                          | No rate                                                                           | `noRateBeforeGstOrForAnUnknownHeading`            |
| 1,000 generated invoices, both supply types                                           | Within half a paisa per tax head (one paisa per rate within a state); CGST = SGST | `roundingOncePerRateIsWithinHalfAPaisaPerTaxHead` |
| HSN 1234 on line 2; a date before GST                                                 | `422` naming the line                                                             | `anUnknownHsnOrADateBeforeGstIs422NamingTheLine`  |
| State 99 or KA; no lines; HSN 847; price 0; quantity 1.5; date 13-10-2026; empty body | `400`                                                                             | `badFieldsAre400`                                 |

## The trap

Plausible but wrong

Hard-coding rates and charging IGST on same-state sales.

"18% IGST" is right for many sales, so the bug hides. The first test shows the old code charging ₹863.01 on the office invoice. The second shows that fixing the rates is not enough: rounding each line's CGST and SGST adds 2 paise the CA does not have. The third shows the fixed preview. Making every sale IGST while building turned 2 tests red; ignoring the invoice date turned 4 red.

``` code
package com.billora.invoices;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.math.RoundingMode;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bugs before the fix.
 * Billora (Karnataka) sells the office invoice to a buyer in Karnataka, on 13 Oct 2026.
 */
class WrongTaxTrapTest extends ApiTest {

    static final long[][] OFFICE = {{3, 79900}, {1, 124950}, {1, 54950}, {3, 19950}};   // quantity, unit price

    /** The "before" code: IGST at a hard-coded 18% on every line, rounded line by line. Kept only in tests. */
    static long oldTaxPaise() {
        long tax = 0;
        for (long[] l : OFFICE) {
            tax += BigDecimal.valueOf(l[0] * l[1]).multiply(new BigDecimal("0.18")).setScale(0, RoundingMode.HALF_UP).longValueExact();
        }
        return tax;
    }

    @Test
    void theOldCodeChargesEighteenPercentIgstOnEverything() {
        assertThat(oldTaxPaise()).isEqualTo(86_301);   // Rs 863.01: T-shirts at 18% instead of 5%, and IGST to a same-state buyer
    }

    @Test
    void roundingEachLineAddsTwoPaiseTheCaDoesNotHave() {
        long perLine = 0;
        long[] percent = {5, 18, 18, 18};
        for (int i = 0; i < OFFICE.length; i++) {
            long half = Gst.percentOf(OFFICE[i][0] * OFFICE[i][1], BigDecimal.valueOf(percent[i]).divide(BigDecimal.TWO));
            perLine += 2 * half;   // CGST + SGST
        }
        assertThat(perLine).isEqualTo(55_144);   // each line's 9% ends in half a paisa and rounds up, three times over
    }

    @Test
    void theFixedPreviewSplitsCgstAndSgstAndRoundsOncePerRate() throws Exception {
        preview("2026-10-13", "29", OFFICE_LINES)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.supplyType").value("INTRA_STATE"))
                .andExpect(jsonPath("$.igstPaise").value(0))
                .andExpect(jsonPath("$.cgstPaise").value(27_571))   // 5,993 at 2.5% + 21,578 at 9%
                .andExpect(jsonPath("$.sgstPaise").value(27_571))
                .andExpect(jsonPath("$.totalTaxPaise").value(55_142))
                .andExpect(jsonPath("$.lines[0].ratePercent").value(5));
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |
| Docker   | Not needed for this station                     |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 11 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

The body is in `docs/office-invoice.json`. Change `placeOfSupply` to `27` and compare.

``` code
# Expect cgstPaise 27571, sgstPaise 27571, totalTaxPaise 55142
curl -X POST http://localhost:8080/invoices/tax-preview -H "Content-Type: application/json" -d "@docs/office-invoice.json"
```

## Troubleshooting

| You see                            | Cause                                       | Fix                                                                           |
|------------------------------------|---------------------------------------------|-------------------------------------------------------------------------------|
| `400` Unknown state code           | Only a demo subset of states is configured. | Use one of the codes in `GstState`, or add one.                               |
| `422` No GST rate                  | The HSN heading has no rate on that date.   | Add it to `billora.hsn-rates`, or check the date (GST started on 1 Jul 2017). |
| `release version 25 not supported` | Maven is using an older JDK.                | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`.                      |

## Project layout

``` tree
stations/017-gst-on-invoices/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/billora/invoices/
│   ├── TaxPreviewController.java   ├── TaxPreviewRequest.java   ├── Gst.java
│   ├── GstRates.java               ├── GstState.java            └── InvoicesApplication.java
├── src/main/resources/application.yaml   seller state and rates
├── src/test/java/com/billora/invoices/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/billora/invoices/TaxPreviewController.java`

Does  
Validates the body, finds the place of supply and each line's rate, then builds the summary and totals.

Why  
Totals are sums of the rate-wise summary, so the summary and the totals can never disagree.

Without it  
IGST at 18% on every line.

#### `src/main/java/com/billora/invoices/TaxPreviewRequest.java`

The body with its rules: a two-digit state code, 4-digit HSN headings, whole paise.

#### `src/main/java/com/billora/invoices/GstState.java`

Does  
States with their GST code and name: an enum with data.

Why  
The code is what e-invoices use; the label is what gets printed.

Without it  
Comparing state names as free text.

#### `src/main/java/com/billora/invoices/GstRates.java`

Does  
Rates from configuration: dated sets of price slabs per HSN heading.

Why  
Two `floorEntry` calls: the set valid on the date, then the slab for the price.

Without it  
Rates in Java, changed by a release.

#### `src/main/java/com/billora/invoices/Gst.java`

Does  
Supply type, the rate-wise summary and the one rounding.

Why  
All tax arithmetic in one small class with its own tests.

Without it  
The trap: tax rounded per line.

- A `TreeMap` keyed by `BigDecimal` compares with `compareTo`, so `18` and `18.00` are one rate.
- Within one state, half the rate is computed once and used for both CGST and SGST.

#### `src/main/resources/application.yaml`

The seller's state and the demo rate configuration, with problem bodies for errors and no silent truncation of `1.5`.

#### `src/main/java/com/billora/invoices/InvoicesApplication.java`

Standard Spring Boot entry point; scans the configuration properties.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                              | Test class                   | Result |
|---------------|--------------------------------------------------------------------------|------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (no rate for an HSN)            | `TaxPreviewContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                                     | `WrongTaxTrapTest` (3)       | pass   |
| This station  | Rates on boundary dates and prices; rounding on 1,000 generated invoices | `GstRatesTest` (3)           | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.billora.invoices.GstRatesTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.billora.invoices.WrongTaxTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.billora.invoices.TaxPreviewContractTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/billora/invoices/WrongTaxTrapTest.java`

Written first: the old code's ₹863.01, 2 paise from per-line rounding, and the fixed preview.

#### `src/test/java/com/billora/invoices/TaxPreviewContractTest.java`

Same state, another state, a rate change, and every refusal.

#### `src/test/java/com/billora/invoices/GstRatesTest.java`

The configured rates on their boundary days and prices, and 1,000 generated invoices against the exact tax.

#### `src/test/java/com/billora/invoices/ApiTest.java`

Shared setup: the whole app through MockMvc and the office invoice.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/billora/invoices/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=DiscountChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (11 station tests and 5 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Line discounts

Add an optional `discountPaise` to each line. Tax is on the value after the discount, and the price slab uses the price of one piece after the discount (this station's rule).

**Done when:** all three tests in `DiscountChallengeTest` pass: two ₹2,600 jerseys with ₹400 off are 5%, not 18%.

Hints

- Work out the line's taxable value first, then divide by the quantity for the slab price.
- A discount of the whole line or more is `422`; a negative one is `400` from validation.

#### `challenge/DiscountChallengeTest.java`

``` code
package com.billora.invoices;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: an optional discountPaise per line. Tax is on the value after the discount, and (in this station's
 * rules) the price slab uses the price per piece after the discount. Each line shows its discount.
 */
class DiscountChallengeTest extends ApiTest {

    static String jacket(int quantity, long discountPaise) {
        return "[{\"description\":\"Jersey\",\"hsn\":\"6109\",\"quantity\":" + quantity
                + ",\"unitPricePaise\":260000,\"discountPaise\":" + discountPaise + "}]";
    }

    @Test
    void aDiscountLowersTheTaxableValueAndCanMoveTheSlab() throws Exception {
        preview("2026-10-13", "29", jacket(2, 40_000))            // Rs 2,600 each, Rs 400 off the line: Rs 2,400 a piece
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lines[0].discountPaise").value(40_000))
                .andExpect(jsonPath("$.lines[0].taxableValuePaise").value(480_000))
                .andExpect(jsonPath("$.lines[0].ratePercent").value(5))   // not 18: below the Rs 2,500 slab after the discount
                .andExpect(jsonPath("$.totalTaxPaise").value(24_000));
    }

    @Test
    void withoutADiscountNothingChanges() throws Exception {
        preview("2026-10-13", "29", oneLine("6109", 260_000))
                .andExpect(jsonPath("$.lines[0].discountPaise").value(0))
                .andExpect(jsonPath("$.lines[0].ratePercent").value(18));
    }

    @Test
    void aDiscountOfTheWholeLineOrMoreIsRefused() throws Exception {
        preview("2026-10-13", "29", jacket(1, 260_000)).andExpect(status().isUnprocessableContent());
        preview("2026-10-13", "29", jacket(1, -1)).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## A seller in a union territory

Add Chandigarh (code 04), a union territory. When the seller and the place of supply are both Chandigarh, the second half is UTGST, not SGST. The response gets `utgstPaise`.

**Done when:** both tests in `UnionTerritoryChallengeTest` pass, and the station's tests still pass.

Hints

- Give `GstState` one more piece of data: whether it is a union territory.
- The test sets `billora.seller-state=CHANDIGARH`; the seller's state is already configuration.

#### `challenge/UnionTerritoryChallengeTest.java`

``` code
package com.billora.invoices;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: a seller in Chandigarh (state code 04, a union territory). Inside the same union territory the
 * tax is CGST + UTGST instead of CGST + SGST; to any other state or territory it is IGST, as before.
 */
@TestPropertySource(properties = "billora.seller-state=CHANDIGARH")
class UnionTerritoryChallengeTest extends ApiTest {

    @Test
    void withinTheSameUnionTerritoryItIsCgstAndUtgst() throws Exception {
        preview("2026-10-13", "04", oneLine("8471", 100_000))
                .andExpect(jsonPath("$.sellerState").value("04-Chandigarh"))
                .andExpect(jsonPath("$.supplyType").value("INTRA_STATE"))
                .andExpect(jsonPath("$.cgstPaise").value(9_000))
                .andExpect(jsonPath("$.utgstPaise").value(9_000))
                .andExpect(jsonPath("$.sgstPaise").value(0))
                .andExpect(jsonPath("$.taxSummary[0].utgstPaise").value(9_000))
                .andExpect(jsonPath("$.totalTaxPaise").value(18_000));
    }

    @Test
    void toAStateItIsIgst() throws Exception {
        preview("2026-10-13", "29", oneLine("8471", 100_000))
                .andExpect(jsonPath("$.igstPaise").value(18_000))
                .andExpect(jsonPath("$.utgstPaise").value(0));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Whole rupees on the invoice

Many invoices end with a "round off" line so the amount payable is in whole rupees. Where would you add it: per rate, per tax head, or only on the grand total? What must the API return so an accountant can still match every tax head to the paisa?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old code's tax, and the 2 paise from per-line rounding.
2.  Model states as an enum with their codes; decide the supply type from the seller and the place of supply.
3.  Move rates into configuration as dated slabs; look them up with `floorEntry`; test the boundaries.
4.  Group lines by rate and round once; test 1,000 generated invoices against the exact tax.

## Design alternatives and trade-offs

| Approach                                     | What it costs                                                             | Verdict                |
|----------------------------------------------|---------------------------------------------------------------------------|------------------------|
| Rates in dated configuration, tax per rate   | A configuration format to learn.                                          | Chosen                 |
| Rates hard-coded in Java                     | A release per rate change; old invoices can no longer be recomputed.      | Wrong                  |
| Tax rounded per line                         | Totals drift from the rate-wise summary by paise.                         | Wrong here             |
| Per-line tax shown, adding up to the summary | Needs the remainder rule from station 015 to hand out the rounding paise. | If lines must show tax |
| States as free-text names                    | "Karnataka", "karnataka" and "KA" are three states.                       | Wrong                  |

## Database design

None in this station. With a database: `gst_rates` (hsn, valid_from, from_paise, percent) with a unique key on (hsn, valid_from, from_paise) and a check that the percent is not negative. An invoice stores the rate it used on each line, so a later rate change never rewrites it.

# 3 · Go deeper: Production

Rate changes  
Added as a new dated set before the day they apply, reviewed like code. Invoices dated before the change keep the old rates.

Money  
Whole paise in and out; `BigDecimal` only for the percentage. One rounding per rate and tax head.

Compliance  
Real invoices also need GSTINs, invoice numbers, e-invoice reporting above the turnover limit, and HSN digits that depend on turnover. Check current rules with a tax professional.

Testing  
Every rate set has tests on the day before and the day it starts, and on each side of every price slab.

# 3 · Go deeper: Interview

## Interview takeaways

When do you charge CGST + SGST and when IGST?

Compare the seller's state with the place of supply. The same state means CGST + SGST, half the rate each; different states mean IGST at the full rate.

Why not hard-code GST rates?

They change by date and sometimes by price. Configuration with start dates lets you add a change ahead of time and still recompute an old invoice with the rate valid on its date.

How do you find a slab or a dated rate?

Put the starts in a TreeMap and call floorEntry: the latest start on or before the date, or the price.

Why does rounding per line give a different total?

Each line's rounding error is up to half a paisa, and they can all go the same way. Summing first and rounding once keeps the error to half a paisa per rate.

What is an enum with data?

Each constant carries fields, like a state's code and name, so lookups and labels live in one place and an unknown value cannot exist.

## Self-check rubric

| Area          | Meets the bar                                       | Above the bar                                       |
|---------------|-----------------------------------------------------|-----------------------------------------------------|
| Correctness   | All 11 tests pass.                                  | You can work out the office invoice's tax by hand.  |
| Tax rules     | CGST + SGST versus IGST, from the states.           | You know why the two can differ by a paisa.         |
| Configuration | Rates by date and slab, with boundary tests.        | You can add a rate change without touching Java.    |
| Explanation   | Per-line versus per-rate rounding in two sentences. | How you would show per-line tax that still adds up. |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any tax code:

- Is a rate, or the tax type, a constant in code?
- Which date picks the rate, and is there a test on the day a rate changes?
- Where does rounding happen, and do the totals match a rate-wise summary?
- Are states compared by code, or by free text?
