# Station 034 · Restaurant chain daily sales report

Foundations · 0–1 years · Core · Food delivery · Types: none

Spring Boot 4.1.1 · Java 25 · Streams: groupingBy, reducing, sorted map entries · BigDecimal · java.time zones · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Outlets and sales are generated demo data, not Tiffino's: 7 days of bills for 40 outlets, created with fixed seeds when the app starts. Nothing is read from a real till.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 18 tests.

# 1 · Understand

## The problem in real life

1.  **Every morning, a spreadsheet**

    Someone copies 40 outlets' till totals into a sheet by hand. It takes an hour, and a typo once doubled an outlet's sales.

2.  **The first program is a little wrong**

    It adds rupees as `double`, so ₹293.90 becomes ₹293.89. It also reuses one key object while grouping, and every row comes out labelled with the last bill's outlet and hour.

3.  **The fix**

    Group with immutable keys, add exact decimals, convert to paise once, and count the day from midnight in India.

Money adds up exactly or not at all, and a key must never change once it is in a map.

## What are we building?

`GET /reports/daily-sales?date=…` gives one day's sales for the whole chain: each outlet's total, number of bills and busiest hour, highest first, and the chain's total per hour.

## An everyday analogy

A cashier closing the day: receipts sorted into one envelope per counter, each envelope added up in rupees and paise, envelopes ranked by total. Nobody re-labels an envelope after it is filed.

## How it works in 4 steps

1.  **Find the day's bills**: from midnight to midnight in India.
2.  **Group them** by outlet, by hour, and by outlet and hour.
3.  **Add up each group** exactly, and count the bills.
4.  **Sort and convert**: outlets highest first, amounts to whole paise.

Check yourself: why is a bill at 00:05 on the 14th in India not on the 13th's report, although the server's clock still says the 13th?

The server runs in UTC, five and a half hours behind India. The outlet's day, and the owner's report, follow India's midnight.

## What this station is not

- **No database.** Seven days of generated bills in memory.
- **No refunds or taxes split out.** A bill's amount is what the till printed.
- **No live day.** Reports are for days that are over.

## Key terms

| Term             | Simple meaning                                                  | Everyday example                                     | In this project                            |
|------------------|-----------------------------------------------------------------|------------------------------------------------------|--------------------------------------------|
| **Group by**     | Put items into buckets by a key, then total each bucket.        | Sorting receipts into one envelope per outlet.       | `groupingBy(Sale::outletId, …)`            |
| **Reduce**       | Combine many values into one, two at a time.                    | Adding up a pile of receipts.                        | `reducing(ZERO, Totals::of, Totals::plus)` |
| **BigDecimal**   | An exact decimal number, for amounts like 261.45.               | Counting money in coins, not by weight.              | `Sale.amountRupees`                        |
| **double**       | A fast binary number that cannot store most decimals exactly.   | A ruler with marks that never land on 0.1.           | the trap                                   |
| **Mutable key**  | A map key whose fields can change after it is stored.           | Re-labelling an envelope after filing it.            | `OldDailyReport.OutletHourKey`             |
| **Business day** | The day as the business sees it: midnight to midnight in India. | A shop's day ends at its own midnight, not London's. | `INDIA`                                    |

# 2 · Build: Spec

## Business problem

**Tiffino** (a fictional restaurant chain) has 40 outlets. Owners get daily totals per outlet and per hour from a spreadsheet someone fills by hand.

## Acceptance criteria

On a small test day whose totals can be checked by hand (`Fixture`).

1.  **Given** bills of ₹261.45, ₹157.40 and ₹524.95 at TF-01, **then** its total is exactly 94,380 paise.
2.  **Given** ₹188.95 and ₹104.95 at TF-02, **then** 29,390 paise, not 29,389.
3.  **Given** a bill at 00:05 India time on the 14th and one at 00:10 on the 15th, **then** the first is on the 14th's report and the second is not.
4.  **Given** two outlets with equal totals, **then** the lower outlet id first; two hours with equal sales, **then** the earlier hour is the busiest.
5.  **Given** a day with no bills, `404`; today or a future day, `422`; a missing or malformed date, `400`.

## Requirements

- Amounts are summed exactly (`BigDecimal`) and returned as integer paise.
- Group keys are immutable: `String`, `Integer`, or a record.
- The day and the hours are India's (`Asia/Kolkata`).
- A bill with a fraction of a paisa is an error, not something to round quietly.

## Learning objectives

- Group and total with `Collectors.groupingBy` and `reducing`.
- Sum `BigDecimal` with `reduce`, and know why `double` is wrong for money.
- Sort map entries by value, then by key.
- Compare a stream with a loop, and choose for readability.

# 2 · Build: API contract

## Endpoint

| Method | Path                                   | Purpose                                                    |
|--------|----------------------------------------|------------------------------------------------------------|
| `GET`  | `/reports/daily-sales?date=YYYY-MM-DD` | One day's totals: per outlet (highest first) and per hour. |

## Response fields

| Field                      | Meaning                                                                                              |
|----------------------------|------------------------------------------------------------------------------------------------------|
| `chainTotalPaise`, `bills` | The whole chain for the day.                                                                         |
| `outlets[]`                | `outletId`, `name`, `totalPaise`, `bills`, `busiestHour` (0 to 23, India time). Highest total first. |
| `hours[]`                  | `hour`, `totalPaise`, `bills` for the whole chain. Only hours with bills, in order.                  |

## Status codes

| Status | When                                         |
|--------|----------------------------------------------|
| 200    | A past day with bills                        |
| 400    | No date, or not `YYYY-MM-DD`                 |
| 404    | A past day with no bills                     |
| 422    | Today or later in India: the day is not over |

## Captured examples

Captured with curl from the running app on 15 Oct 2026. The demo data covers the 7 days before the app started, so the capture asks for yesterday. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: yesterday

**Why:** 1,336 bills from 40 outlets, totalled per outlet and per hour.

Request

``` code
GET /reports/daily-sales?date=2026-10-14 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 4636

{
  "date": "2026-10-14",
  "chainTotalPaise": 57635970,
  "bills": 1336,
  "outlets": [
    {
      "outletId": "TF-04",
      "name": "Tiffino Whitefield",
      "totalPaise": 2227890,
      "bills": 49,
      "busiestHour": 16
    },
    {
      "outletId": "TF-17",
      "name": "Tiffino Kalyan Nagar",
      "totalPaise": 2016315,
      "bills": 45,
      "busiestHour": 8
    },
    {
      "outletId": "TF-29",
      "name": "Tiffino Kharadi",
      "totalPaise": 1969485,
      "bills": 44,
      "busiestHour": 17
    },
    {
      "outletId": "TF-34",
      "name": "Tiffino Pimple Saudagar",
      "totalPaise": 1959720,
      "bills": 43,
      "busiestHour": 10
    },
    {
      "outletId": "TF-35",
      "name": "Tiffino Kalyani Nagar",
      "totalPaise": 1954365,
      "bills": 43,
      "busiestHour": 9
    },
    {
      "outletId": "TF-14",
      "name": "Tiffino Rajajinagar",
      "totalPaise": 1893465,
      "bills": 49,
      "busiestHour": 14
    },
    {
      "outletId": "TF-03",
      "name": "Tiffino HSR Layout",
      "totalPaise": 1893150,
      "bills": 44,
      "busiestHour": 11
    },
    {
      "outletId": "TF-01",
      "name": "Tiffino Koramangala",
      "totalPaise": 1856610,
      "bills": 43,
      "busiestHour": 20
    },
    {
      "outletId": "TF-30",
      "name": "Tiffino Shivajinagar",
      "totalPaise": 1747830,
      "bills": 49,
      "busiestHour": 15
    },
    {
      "outletId": "TF-24",
      "name": "Tiffino Baner",
      "totalPaise": 1736910,
      "bills": 41,
      "busiestHour": 9
    },
    {
      "outletId": "TF-10",
      "name": "Tiffino Hebbal",
      "totalPaise": 1719165,
      "bills": 38,
      "busiestHour": 11
    },
    {
      "outletId": "TF-38",
      "name": "Tiffino Wagholi",
      "totalPaise": 1615425,
      "bills": 36,
      "busiestHour": 8
    },
    {
      "outletId": "TF-32",
      "name": "Tiffino Deccan",
      "totalPaise": 1610700,
      "bills": 39,
      "busiestHour": 19
    },
    {
      "outletId": "TF-13",
      "name": "Tiffino JP Nagar",
      "totalPaise": 1569540,
      "bills": 33,
      "busiestHour": 13
    },
    {
      "outletId": "TF-31",
      "name": "Tiffino Camp",
      "totalPaise": 1557990,
      "bills": 36,
      "busiestHour": 10
    },
    {
      "outletId": "TF-11",
      "name": "Tiffino Yelahanka",
      "totalPaise": 1525650,
      "bills": 33,
      "busiestHour": 19
    },
    {
      "outletId": "TF-36",
      "name": "Tiffino Sinhagad Road",
      "totalPaise": 1521975,
      "bills": 33,
      "busiestHour": 14
    },
    {
      "outletId": "TF-39",
      "name": "Tiffino Undri",
      "totalPaise": 1439865,
      "bills": 34,
      "busiestHour": 17
    },
    {
      "outletId": "TF-12",
      "name": "Tiffino Banashankari",
      "totalPaise": 1426320,
      "bills": 33,
      "busiestHour": 13
    },
    {
      "outletId": "TF-16",
      "name": "Tiffino Sarjapur Road",
      "totalPaise": 1365525,
      "bills": 33,
      "busiestHour": 19
    },
    {
      "outletId": "TF-33",
      "name": "Tiffino Magarpatta",
      "totalPaise": 1358910,
      "bills": 33,
      "busiestHour": 12
    },
    {
      "outletId": "TF-18",
      "name": "Tiffino Basavanagudi",
      "totalPaise": 1314495,
      "bills": 31,
      "busiestHour": 11
    },
    {
      "outletId": "TF-23",
      "name": "Tiffino Kothrud",
      "totalPaise": 1306305,
      "bills": 27,
      "busiestHour": 9
    },
    {
      "outletId": "TF-37",
      "name": "Tiffino Bavdhan",
      "totalPaise": 1248450,
      "bills": 30,
      "busiestHour": 19
    },
    {
      "outletId": "TF-27",
      "name": "Tiffino Wakad",
      "totalPaise": 1234695,
      "bills": 31,
      "busiestHour": 20
    },
    {
      "outletId": "TF-26",
      "name": "Tiffino Hinjewadi",
      "totalPaise": 1231860,
      "bills": 27,
      "busiestHour": 18
    },
    {
      "outletId": "TF-09",
      "name": "Tiffino Electronic City",
      "totalPaise": 1223355,
      "bills": 25,
      "busiestHour": 9
    },
    {
      "outletId": "TF-15",
      "name": "Tiffino Bellandur",
      "totalPaise": 1205820,
      "bills": 30,
      "busiestHour": 8
    },
    {
      "outletId": "TF-21",
      "name": "Tiffino Koregaon Park",
      "totalPaise": 1190490,
      "bills": 27,
      "busiestHour": 19
    },
    {
      "outletId": "TF-07",
      "name": "Tiffino BTM Layout",
      "totalPaise": 1170330,
      "bills": 27,
      "busiestHour": 11
    },
    {
      "outletId": "TF-06",
      "name": "Tiffino Malleshwaram",
      "totalPaise": 1157520,
      "bills": 25,
      "busiestHour": 17
    },
    {
      "outletId": "TF-19",
      "name": "Tiffino Frazer Town",
      "totalPaise": 1147440,
      "bills": 29,
      "busiestHour": 10
    },
    {
      "outletId": "TF-20",
      "name": "Tiffino Ulsoor",
      "totalPaise": 1132320,
      "bills": 29,
      "busiestHour": 13
    },
    {
      "outletId": "TF-22",
      "name": "Tiffino Viman Nagar",
      "totalPaise": 1092630,
      "bills": 28,
      "busiestHour": 10
    },
    {
      "outletId": "TF-08",
      "name": "Tiffino Marathahalli",
      "totalPaise": 1054305,
      "bills": 20,
      "busiestHour": 10
    },
    {
      "outletId": "TF-02",
      "name": "Tiffino Indiranagar",
      "totalPaise": 1052835,
      "bills": 26,
      "busiestHour": 20
    },
    {
      "outletId": "TF-28",
      "name": "Tiffino Hadapsar",
      "totalPaise": 1052100,
      "bills": 27,
      "busiestHour": 13
    },
    {
      "outletId": "TF-40",
      "name": "Tiffino Erandwane",
      "totalPaise": 1005690,
      "bills": 25,
      "busiestHour": 14
    },
    {
      "outletId": "TF-05",
      "name": "Tiffino Jayanagar",
      "totalPaise": 968940,
      "bills": 20,
      "busiestHour": 11
    },
    {
      "outletId": "TF-25",
      "name": "Tiffino Aundh",
      "totalPaise": 879585,
      "bills": 21,
      "busiestHour": 20
    }
  ],
  "hours": [
    {
      "hour": 8,
      "totalPaise": 4532220,
      "bills": 104
    },
    {
      "hour": 9,
      "totalPaise": 4796820,
      "bills": 104
    },
    {
      "hour": 10,
      "totalPaise": 3356430,
      "bills": 79
    },
    {
      "hour": 11,
      "totalPaise": 4487700,
      "bills": 105
    },
    {
      "hour": 12,
      "totalPaise": 2979900,
      "bills": 72
    },
    {
      "hour": 13,
      "totalPaise": 3890250,
      "bills": 90
    },
    {
      "hour": 14,
      "totalPaise": 3695370,
      "bills": 84
    },
    {
      "hour": 15,
      "totalPaise": 3064635,
      "bills": 74
    },
    {
      "hour": 16,
      "totalPaise": 3216990,
      "bills": 76
    },
    {
      "hour": 17,
      "totalPaise": 4113690,
      "bills": 94
    },
    {
      "hour": 18,
      "totalPaise": 4136160,
      "bills": 98
    },
    {
      "hour": 19,
      "totalPaise": 3810975,
      "bills": 88
    },
    {
      "hour": 20,
      "totalPaise": 4681110,
      "bills": 102
    },
    {
      "hour": 21,
      "totalPaise": 3405570,
      "bills": 81
    },
    {
      "hour": 22,
      "totalPaise": 3468150,
      "bills": 85
    }
  ]
}
```

### Case 2: eight days ago

**Why:** before the demo data starts: `404`.

Request

``` code
GET /reports/daily-sales?date=2026-10-07 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No sales were recorded on 2026-10-07.",
  "instance": "/reports/daily-sales",
  "status": 404,
  "title": "No sales"
}
```

### Case 3: today

**Why:** the day has not ended in India: `422`.

Request

``` code
GET /reports/daily-sales?date=2026-10-15 HTTP/1.1
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "2026-10-15 has not ended in India yet; reports are for past days.",
  "instance": "/reports/daily-sales",
  "status": 422,
  "title": "Day not over"
}
```

### Case 4: `14-10-2026`

**Why:** not ISO: `400`.

Request

``` code
GET /reports/daily-sales?date=14-10-2026 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to convert 'date' with value: '14-10-2026'",
  "instance": "/reports/daily-sales",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: no date

**Why:** `400`.

Request

``` code
GET /reports/daily-sales HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Required parameter 'date' is not present.",
  "instance": "/reports/daily-sales",
  "status": 400,
  "title": "Bad Request"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                         | What happens                                  | Proved by                                                     |
|--------------------------------------------------------------|-----------------------------------------------|---------------------------------------------------------------|
| Bills at 00:05 on the day and 00:10 the next day, India time | The first counts, the second does not         | `theDayIsMidnightToMidnightInIndia`                           |
| Names, bill counts and busiest hours                         | As on the fixture                             | `eachOutletHasNameBillsAndBusiestHour`                        |
| Equal totals; equal hours                                    | Lower id first; earlier hour                  | `equalTotalsAreOrderedByOutletIdAndEqualHoursByTheEarlierOne` |
| A bill of ₹10.005                                            | An error, not a rounding                      | `aFractionOfAPaisaIsAnErrorNotARounding`                      |
| Seven days of demo bills                                     | A plain loop over paise gives the same totals | `bothWaysGiveTheSameTotals`                                   |
| The whole response                                           | Exactly as expected, field by field           | `aClosedDayHasTotalsPerOutletAndPerHour`                      |
| No bills; today; next year; no date; 30 February             | `404`; `422`; `422`; `400`; `400`             | `DailySalesContractTest`                                      |

## The trap

Plausible but wrong

Summing money in double, and grouping by a mutable key.

The first test shows `(188.95 + 104.95) * 100` is `29389.999999999996` in `double`, so the old report gave TF-02 29,389 paise for 29,390 of bills. The second shows the reused key: the map has several entries, and every one reads "TF-03 20", the last bill's outlet and hour, because they are all the same object. The third shows the real report's exact, correctly labelled rows. While building, each fix was undone once. Hours in UTC turned 2 tests red, and a UTC day 4. Ascending order turned 3 red, and a `double` sum 11 (the paise conversion refuses the drift). Ties going to the later hour turned 1 red, and allowing today's report 1.

``` code
package com.tiffino.reports;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: the old report's two bugs, on the fixture day. */
class DoubleMoneyMutableKeyTrapTest {

    static final List<Sale> DAY = Fixture.FEED.between(Fixture.DAY.atStartOfDay(DailySalesReport.INDIA).toInstant(),
            Fixture.DAY.plusDays(1).atStartOfDay(DailySalesReport.INDIA).toInstant());

    @Test
    void summingInDoubleLosesAPaisa() {
        assertThat((188.95 + 104.95) * 100).isEqualTo(29_389.999999999996);   // and a cast to long cuts off the .999
        assertThat(OldDailyReport.outletTotalPaise(DAY, "TF-02")).isEqualTo(29_389);   // ₹293.89 for ₹293.90 of bills
    }

    @Test
    void aReusedMutableKeyLabelsEveryRowWithTheLastSale() {
        var old = OldDailyReport.byOutletHour(DAY);
        assertThat(old.size()).isGreaterThan(1);
        assertThat(old.keySet()).allSatisfy(k -> assertThat(k.outlet + " " + k.hour).isEqualTo("TF-03 20"));
    }

    @Test
    void theRealReportIsExactAndLabelledCorrectly() {
        var report = new DailySalesReport(Fixture.FEED, new Outlets(), Fixture.CLOCK).forDay(Fixture.DAY);
        assertThat(report.outlets()).extracting(DailySalesReport.OutletRow::outletId, DailySalesReport.OutletRow::totalPaise)
                .containsExactly(
                        org.assertj.core.groups.Tuple.tuple("TF-01", 94_380L),
                        org.assertj.core.groups.Tuple.tuple("TF-03", 45_890L),
                        org.assertj.core.groups.Tuple.tuple("TF-02", 29_390L));
    }
}
```

``` code
package com.tiffino.reports;

import java.time.ZoneId;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** The report as the spreadsheet macro's replacement first did it, kept only in tests. */
final class OldDailyReport {

    /** A mutable key: equals and hashCode read fields that the loop below keeps changing. */
    static final class OutletHourKey {
        String outlet;
        int hour;

        @Override
        public boolean equals(Object o) {
            return o instanceof OutletHourKey k && k.hour == hour && Objects.equals(k.outlet, outlet);
        }

        @Override
        public int hashCode() {
            return Objects.hash(outlet, hour);
        }
    }

    private OldDailyReport() {
    }

    static Map<OutletHourKey, Double> byOutletHour(List<Sale> sales) {
        Map<OutletHourKey, Double> totals = new HashMap<>();
        OutletHourKey key = new OutletHourKey();   // one object, reused "to save allocations"
        for (Sale s : sales) {
            key.outlet = s.outletId();
            key.hour = s.at().atZone(ZoneId.of("Asia/Kolkata")).getHour();
            totals.merge(key, s.amountRupees().doubleValue(), Double::sum);
        }
        return totals;
    }

    static long outletTotalPaise(List<Sale> sales, String outletId) {
        double rupees = 0;
        for (Sale s : sales) {
            if (s.outletId().equals(outletId)) {
                rupees += s.amountRupees().doubleValue();
            }
        }
        return (long) (rupees * 100);   // 293.9 * 100 is 29389.999999999996 in double
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
./mvnw test                 # all 18 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask for yesterday (India's date). On macOS use `date -v-1d +%F` instead of `date -d yesterday +%F`.

``` code
curl "http://localhost:8080/reports/daily-sales?date=$(TZ=Asia/Kolkata date -d yesterday +%F)"
```

Then open `jshell` and type `(188.95 + 104.95) * 100`.

## Troubleshooting

| You see                                          | Cause                                                                        | Fix                                                                                       |
|--------------------------------------------------|------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| `ArithmeticException: Rounding necessary`        | An amount with more than two decimals reached `longValueExact`.              | Find the bill: tills print paise; a third decimal is a data problem to fix at the source. |
| Yesterday's report is `404`                      | The demo data covers the 7 days before the app started, in India's calendar. | Use India's date: `TZ=Asia/Kolkata date -d yesterday +%F`.                                |
| A `groupingBy` map in a different order each run | `HashMap` has no order.                                                      | Sort the entries, or collect into a `TreeMap` as the hours do.                            |

## Project layout

``` tree
stations/034-restaurant-chain-daily-sales-report/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tiffino/reports/
│   ├── ReportController.java   ├── DailySalesReport.java
│   ├── Sale.java   ├── SalesFeed.java   ├── DemoSalesFeed.java
│   ├── Outlets.java   └── ReportsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/tiffino/reports/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the pieces it uses.

#### `src/main/java/com/tiffino/reports/ReportController.java`

Does  
Reads an ISO date and returns the report.

Why  
Spring turns a missing or malformed date into a 400 on its own.

Without it  
Accepting a date as a string and parsing it by hand.

#### `src/main/java/com/tiffino/reports/DailySalesReport.java`

Does  
Finds the day's bills and groups, totals, sorts and converts them.

Why  
Three `groupingBy` calls into an immutable `Totals` record; the composite key is a record; paise once, at the end.

Without it  
`double` totals, and a key object reused while grouping.

- `reducing(identity, mapper, op)` turns each bill into `Totals` and adds them.
- Sorting entries: `comparingByValue(...).reversed().thenComparing(comparingByKey())`.
- `longValueExact()` throws rather than rounding a fraction of a paisa.

#### `src/main/java/com/tiffino/reports/Sale.java`

One bill, with the amount as the till printed it.

#### `src/main/java/com/tiffino/reports/SalesFeed.java`

Where bills come from: every bill in a time range.

#### `src/main/java/com/tiffino/reports/DemoSalesFeed.java`

Seven days of seeded demo bills for 40 outlets, menu price plus 5% GST.

#### `src/main/java/com/tiffino/reports/Outlets.java`

The 40 outlets' ids and names.

#### `src/main/java/com/tiffino/reports/ReportsApplication.java`

Entry point, and the `Clock` bean tests replace.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                 | Test class                          | Result |
|---------------|---------------------------------------------|-------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found    | `DailySalesContractTest` (4)        | pass   |
| Every station | Reproduce the failure before the fix        | `DoubleMoneyMutableKeyTrapTest` (3) | pass   |
| This station  | Day edges, order, ties, bad amounts         | `DailySalesReportTest` (4)          | pass   |
| This station  | Streams and a loop agree on 7 days of bills | `StreamsAndLoopAgreeTest` (7 runs)  | pass   |

## Streams or a loop?

|          | Streams (the report)                                  | Loop (the test's check)                      |
|----------|-------------------------------------------------------|----------------------------------------------|
| Reads as | What is computed: group, total, sort                  | How: walk, look up, add                      |
| Good for | Several groupings of the same data, sorting, chaining | One simple total; early exit; complex state  |
| Here     | Three groupings and a sort                            | An independent second way to the same totals |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.reports.DailySalesContractTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.reports.StreamsAndLoopAgreeTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.reports.DailySalesReportTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.reports.DoubleMoneyMutableKeyTrapTest
[INFO] Tests run: 18, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tiffino/reports/Fixture.java`

A day small enough to check by hand, with a bill just outside each end.

#### `src/test/java/com/tiffino/reports/DoubleMoneyMutableKeyTrapTest.java`

Written first: the double paisa, the mislabelled rows, and the exact report.

#### `src/test/java/com/tiffino/reports/DailySalesReportTest.java`

The report without Spring: India's day, names, ties, a fraction of a paisa.

#### `src/test/java/com/tiffino/reports/StreamsAndLoopAgreeTest.java`

A loop over whole paise checks the streams on 7 demo days.

#### `src/test/java/com/tiffino/reports/DailySalesContractTest.java`

The full response compared strictly, and every refusal.

#### `src/test/java/com/tiffino/reports/OldDailyReport.java`

The old code, kept only in tests.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tiffino/reports/`.
2.  Run it: `./mvnw test -Dtest=WeeklyTotalsChallengeTest`. It does not compile until the new method exists; add an empty one and watch the test fail.
3.  Change the code until it passes, then run `./mvnw test` to check the other 18 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 22 tests pass (18 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## A week at a glance

Add `weekTotals(lastDay)`: each outlet's total in paise for the 7 India days ending on `lastDay`, highest first. It must agree with the seven daily reports, and a week that includes today is refused.

**Done when:** both tests in `WeeklyTotalsChallengeTest` pass.

Hints

- The same grouping as the daily report, over a longer time range.
- A `LinkedHashMap` keeps the order you put entries in.

#### `challenge/WeeklyTotalsChallengeTest.java`

``` code
package com.tiffino.reports;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Challenge 1: owners want a week at a glance. Add DailySalesReport.weekTotals(lastDay): each outlet's total in paise
 * for the 7 India days ending on lastDay, highest first (a LinkedHashMap keeps that order). It must agree with the
 * seven daily reports, and a week that includes today is refused like a day that is not over.
 */
class WeeklyTotalsChallengeTest {

    static final Outlets OUTLETS = new Outlets();
    static final DailySalesReport REPORT = new DailySalesReport(new DemoSalesFeed(Fixture.CLOCK, OUTLETS), OUTLETS, Fixture.CLOCK);

    @Test
    void theWeekIsTheSumOfItsDaysHighestFirst() {
        LocalDate last = Fixture.DAY;
        Map<String, Long> week = REPORT.weekTotals(last);
        assertThat(week).hasSize(40);
        for (String outlet : OUTLETS.ids()) {
            long sum = 0;
            for (int i = 0; i < 7; i++) {
                sum += REPORT.forDay(last.minusDays(i)).outlets().stream().filter(o -> o.outletId().equals(outlet)).findFirst().orElseThrow().totalPaise();
            }
            assertThat(week.get(outlet)).as(outlet).isEqualTo(sum);
        }
        var totals = new ArrayList<>(week.values());
        assertThat(totals).isSortedAccordingTo(Comparator.reverseOrder());
    }

    @Test
    void aWeekEndingTodayIsNotOverYet() {
        assertThatThrownBy(() -> REPORT.weekTotals(Fixture.DAY.plusDays(1))).isInstanceOf(org.springframework.web.ErrorResponseException.class);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## The busiest hour in each city

TF-01 to TF-20 are in Bengaluru, TF-21 to TF-40 in Pune. Add `Outlets.city` and `busiestHourByCity(day)`: each city's hour with the highest sales across its outlets, the earlier hour on a tie.

**Done when:** both tests in `CityPeakHourChallengeTest` pass.

Hints

- `groupingBy` can take another `groupingBy` as its downstream collector: city, then hour.
- For each city's inner map, the entry with the highest amount, with the hour as a tie-break.

#### `challenge/CityPeakHourChallengeTest.java`

``` code
package com.tiffino.reports;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: TF-01 to TF-20 are in Bengaluru, TF-21 to TF-40 in Pune. Add Outlets.city(outletId) and
 * DailySalesReport.busiestHourByCity(day): for each city, the hour with the highest sales across its outlets
 * (earlier hour on a tie). One stream, grouping by city and then by hour.
 */
class CityPeakHourChallengeTest {

    @Test
    void eachCityHasItsOwnPeak() {
        var day = Fixture.DAY;
        List<Sale> sales = List.of(
                Fixture.sale("TF-01", day, "13:10", "100.00"),
                Fixture.sale("TF-02", day, "13:40", "50.00"),
                Fixture.sale("TF-03", day, "20:00", "120.00"),
                Fixture.sale("TF-21", day, "20:15", "80.00"),
                Fixture.sale("TF-22", day, "09:05", "70.00"),
                Fixture.sale("TF-22", day, "10:30", "20.00"));
        var report = new DailySalesReport((from, to) -> sales, new Outlets(), Fixture.CLOCK);
        assertThat(report.busiestHourByCity(day)).isEqualTo(Map.of("Bengaluru", 13, "Pune", 20));
    }

    @Test
    void outletsKnowTheirCity() {
        Outlets outlets = new Outlets();
        assertThat(outlets.city("TF-20")).isEqualTo("Bengaluru");
        assertThat(outlets.city("TF-21")).isEqualTo("Pune");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Compute on request, or once a night?

With 400 outlets and a year of history, owners want any day, week or month in under a second. Compare computing from bills on each request with storing one row per outlet per day after midnight. What happens when a late bill or a refund arrives for a day already totalled?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test on a day small enough to add up by hand.
2.  Fix the day's edges in India's time zone.
3.  Group into an immutable totals record; use a record for the composite key.
4.  Sort entries, convert to paise once, and check the streams against a plain loop.

## Design alternatives and trade-offs

| Approach                                            | What it costs                                                 | Verdict         |
|-----------------------------------------------------|---------------------------------------------------------------|-----------------|
| `BigDecimal` from the till's text, paise in the API | Exact; slower than `long` (irrelevant at this size).          | Chosen          |
| Parse straight to `long` paise                      | Exact and fast; needs a careful parser for "261.4" and "261". | Also fine       |
| `double` rupees                                     | Off by a paisa after a few additions.                         | The trap        |
| A reused mutable key                                | Every row labelled with the last bill.                        | The trap        |
| SQL `GROUP BY` in the database                      | The usual choice once bills are in a table.                   | With a database |

## Database design

None in this station. With a table, `bill(outlet_id, billed_at timestamptz, amount_paise bigint check (amount_paise > 0))`, and the report is one `GROUP BY outlet_id, extract(hour from billed_at at time zone 'Asia/Kolkata')` over the day's range.

# 3 · Go deeper: Production

Late data  
Tills go offline and send bills hours later. A report for yesterday can change; say when it was computed, or close the day only after every outlet has synced.

Time zones  
Store instants; convert to India's time only to decide the day and the hour.

Size  
1,400 bills a day fit in memory easily. At millions, group in the database or keep daily totals.

Money  
Use `BigDecimal` or integer paise everywhere money flows; one `double` in the middle undoes it.

# 3 · Go deeper: Interview

## Interview takeaways

Why not use double for money?

double is binary floating point; most decimal amounts like 0.1 or 188.95 cannot be stored exactly, and the errors show up after additions or when converting to paise. Use BigDecimal or integer minor units.

What happens if you mutate an object used as a HashMap key?

Its hashCode changes, so the map looks in the wrong bucket: lookups fail and entries can be duplicated. Keys must be immutable; records with final fields are ideal.

How do you sum BigDecimal in a stream?

map to the amount, then reduce(BigDecimal.ZERO, BigDecimal::add). Inside groupingBy, use reducing(BigDecimal.ZERO, mapper, BigDecimal::add).

How do you sort a map by value?

Stream its entrySet and sort with Map.Entry.comparingByValue(), reversed for highest first, thenComparing(comparingByKey()) to make ties stable.

Streams or loops?

Whichever reads more clearly. Streams suit grouping, mapping and sorting pipelines; loops suit early exit and complex state. Performance is rarely the deciding factor at this size.

## Self-check rubric

| Area        | Meets the bar                           | Above the bar                                       |
|-------------|-----------------------------------------|-----------------------------------------------------|
| Correctness | All 18 tests pass.                      | You found a double sum that loses a paisa yourself. |
| Streams     | groupingBy with a downstream collector. | Nested grouping and sorted entries.                 |
| Money       | BigDecimal or paise, never double.      | You know where the conversion to paise belongs.     |
| Time        | The day in India's time zone.           | Late bills and when a day is final.                 |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any report:

- Does a `double` or `float` touch money anywhere?
- Can any map key change after it is stored?
- Whose midnight does "a day" use?
- Is the order of rows defined, including ties?
