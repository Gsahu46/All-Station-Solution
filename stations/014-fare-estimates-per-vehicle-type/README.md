# Station 014 · Fare estimates per vehicle type

Foundations · 0–1 years · Core · Ride-hailing · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · strategy pattern · BigDecimal · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Fares are estimates from demo rates, not any city's tariff. Road distance is the straight-line distance times 1.3, not a routing service. No ride is booked.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **Rydo's fare code is one long if-else**

    Bikes, autos and cabs are priced in a 300-line method with shared variables at the top.

2.  **Someone adds "cab XL"**

    To make XL work, they change a shared default. Auto fares, which nobody touched, quietly rise from ₹150 to ₹190 for a 10 km ride.

3.  **The fix**

    Each vehicle type owns its fare rule. The estimator asks every type the same question. Adding a type adds a line; it cannot change another type's fare.

When rules for different things share one method and its variables, changing one thing changes the others. Give each thing its own rule.

## What are we building?

`GET /fare-estimates?pickup=lat,lng&drop=lat,lng`: the server works out the road distance and returns a fare for every vehicle type. The client sends only the two points; it can never send a distance or a price.

## An everyday analogy

A railway station has a separate fare chart for sleeper, 3A and 2A. When a new coach class is introduced, the railway prints a new chart; nobody edits the sleeper chart. One big chart with footnotes like "for 2A use the 3A rate plus…" is where mistakes creep in.

## How it works in 4 steps

1.  **Read the two points** and check they are inside the service area.
2.  **Work out the distance** on the server, rounded to 0.1 km.
3.  **Ask every vehicle type** for its fare at that distance; each type's rule answers in its own way.
4.  **Round to whole rupees** (half up) and return paise.

Check yourself: why not let the app send the distance it already shows on the map?

Because then anyone could send `distanceKm=1` for a 30 km ride and get a ₹30 fare. Anything that sets a price must be computed on the server from inputs the client cannot bend.

## What this station is not

- **Not real fares.** Rates are demo rules.
- **Not real road distance.** Straight-line distance × 1.3; production asks a routing service.
- **No surge, no booking.** An estimate only.

## Key terms

| Term                      | Simple meaning                                                              | Everyday example                                                            | In this project                        |
|---------------------------|-----------------------------------------------------------------------------|-----------------------------------------------------------------------------|----------------------------------------|
| **Strategy pattern**      | Put each way of doing a job in its own object, and let the caller pick one. | Each counter in a bank has its own rules; you just go to the right counter. | `FareRule`, held by each vehicle type. |
| **Polymorphism**          | Calling the same method on different objects, each answering its own way.   | Asking every shop "what's the price?"                                       | `rule.fare(km)`                        |
| **Open/closed principle** | Add new behaviour by adding code, not by editing code that already works.   | Adding a new counter without rebuilding the old ones.                       | A new vehicle type is one new line.    |
| **BigDecimal**            | Java's exact decimal number. `double` cannot hold 0.1 exactly.              | Counting coins instead of weighing them.                                    | Every fare calculation.                |
| **Rounding half up**      | 0.5 and above rounds up; below rounds down.                                 | ₹57.50 is charged as ₹58.                                                   | `RoundingMode.HALF_UP`                 |
| **Paise**                 | Whole hundredths of a rupee: no decimals in the answer.                     | ₹140 is 14000 paise.                                                        | `farePaise`                            |

# 2 · Build: Spec

## Business problem

**Rydo** (a fictional ride-hailing app in Bengaluru) prices bike, auto and cab rides in one long if-else. Adding "cab XL" changed a shared default and raised every auto fare; drivers noticed before the engineers did. The old app also sent the distance it computed, which a modified app could fake.

## Acceptance criteria

1.  **Given** MG Road to Koramangala, **then** the distance is 6.4 km and fares are bike ₹58, auto ₹96, cab ₹140, cab XL ₹208.
2.  **Given** the same point twice, **then** each vehicle's minimum: ₹30, ₹30, ₹80, ₹120.
3.  **Given** extra `distanceKm` or `fare` parameters, **then** they are ignored.
4.  **Given** a malformed or missing location, **then** `400`; outside the service area, `422`.
5.  **Given** a new vehicle type, **then** no existing fare changes.

## Requirements

- Rates (demo rules): bike ₹20 + ₹6/km, min ₹30; auto ₹30 for the first 2 km + ₹15/km after; cab ₹50 + ₹14/km, min ₹80; cab XL ₹80 + ₹20/km, min ₹120.
- Money is `BigDecimal` from strings; the answer is whole rupees (half up), returned in paise.
- Distance is computed on the server, rounded to 0.1 km, and the fare uses that rounded number.
- Service area: a demo rectangle around Bengaluru.

## Learning objectives

- Replace an if-else chain with the strategy pattern: an interface and one rule per type.
- Put behaviour on an enum, and explain the open/closed principle.
- Calculate money with `BigDecimal` and an explicit rounding mode.
- Explain why price inputs must never come from the client.

# 2 · Build: API contract

## Endpoint

| Method | Path                                          | Purpose                                     |
|--------|-----------------------------------------------|---------------------------------------------|
| `GET`  | `/fare-estimates?pickup=lat,lng&drop=lat,lng` | Distance and a fare for every vehicle type. |

## Status codes

| Status | When                                               |
|--------|----------------------------------------------------|
| 200    | Both points valid and in the service area          |
| 400    | A point is missing, not `lat,lng`, or out of range |
| 422    | A point is outside the service area                |

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: MG Road to Koramangala

**Why:** 6.4 km by the server's estimate. Each vehicle's rule gives its own fare: the cab's ₹139.60 rounds half up to ₹140.

Request

``` code
GET /fare-estimates?pickup=12.9756,77.6066&drop=12.9352,77.6245 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 255

{
  "pickup": {
    "lat": 12.9756,
    "lng": 77.6066
  },
  "drop": {
    "lat": 12.9352,
    "lng": 77.6245
  },
  "distanceKm": 6.4,
  "estimates": [
    {
      "vehicle": "BIKE",
      "farePaise": 5800
    },
    {
      "vehicle": "AUTO",
      "farePaise": 9600
    },
    {
      "vehicle": "CAB",
      "farePaise": 14000
    },
    {
      "vehicle": "CAB_XL",
      "farePaise": 20800
    }
  ]
}
```

### Case 2: a client tries to set the distance

**Why:** `distanceKm=1` and `fare=10` are not parameters of this endpoint; the answer is the same as case 1.

Request

``` code
GET /fare-estimates?pickup=12.9756,77.6066&drop=12.9352,77.6245&distanceKm=1&fare=10 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 255

{
  "pickup": {
    "lat": 12.9756,
    "lng": 77.6066
  },
  "drop": {
    "lat": 12.9352,
    "lng": 77.6245
  },
  "distanceKm": 6.4,
  "estimates": [
    {
      "vehicle": "BIKE",
      "farePaise": 5800
    },
    {
      "vehicle": "AUTO",
      "farePaise": 9600
    },
    {
      "vehicle": "CAB",
      "farePaise": 14000
    },
    {
      "vehicle": "CAB_XL",
      "farePaise": 20800
    }
  ]
}
```

### Case 3: pickup equals drop

**Why:** 0 km, so each vehicle's minimum fare.

Request

``` code
GET /fare-estimates?pickup=12.9756,77.6066&drop=12.9756,77.6066 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 254

{
  "pickup": {
    "lat": 12.9756,
    "lng": 77.6066
  },
  "drop": {
    "lat": 12.9756,
    "lng": 77.6066
  },
  "distanceKm": 0.0,
  "estimates": [
    {
      "vehicle": "BIKE",
      "farePaise": 3000
    },
    {
      "vehicle": "AUTO",
      "farePaise": 3000
    },
    {
      "vehicle": "CAB",
      "farePaise": 8000
    },
    {
      "vehicle": "CAB_XL",
      "farePaise": 12000
    }
  ]
}
```

### Case 4: a place name instead of coordinates

**Why:** `400`; the app must send coordinates.

Request

``` code
GET /fare-estimates?pickup=MG%20Road&drop=12.9352,77.6245 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "'pickup' must be latitude,longitude, like 12.9756,77.6066.",
  "instance": "/fare-estimates",
  "status": 400,
  "title": "Invalid location"
}
```

### Case 5: a drop in Mumbai

**Why:** a valid point, but outside the service area: `422`.

Request

``` code
GET /fare-estimates?pickup=12.9756,77.6066&drop=19.0760,72.8777 HTTP/1.1
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "'drop' is outside the area Rydo serves.",
  "instance": "/fare-estimates",
  "status": 422,
  "title": "Outside service area"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                  | What happens                           | Proved by                                              |
|---------------------------------------|----------------------------------------|--------------------------------------------------------|
| MG Road → Koramangala                 | 6.4 km; ₹58, ₹96, ₹140, ₹208           | `everyVehicleTypeGetsAnEstimateFromTheServersDistance` |
| Same point                            | Each minimum                           | `aVeryShortRidePaysEachMinimum`                        |
| Client sends distance or fare         | Ignored                                | `distanceOrFareSentByTheClientIsIgnored`               |
| Auto at 0, 2.0, 2.1, 3.0 km           | ₹30, ₹30, ₹32, ₹45                     | `theAutoMeterIncludesTheFirstTwoKm`                    |
| Short bike and cab rides              | Minimums, then per-km                  | `minimumsApplyToShortRides`                            |
| ₹57.50, ₹139.60                       | ₹58, ₹140                              | `halfARupeeRoundsUp`                                   |
| 0.1 + 0.2                             | `double` is off; `BigDecimal` is exact | `doubleArithmeticIsNotExactForMoney`                   |
| Place name, latitude 95, missing drop | `400`                                  | `aMalformedOrMissingLocationIs400`                     |
| Mumbai                                | `422`                                  | `aPointOutsideTheServiceAreaIs422`                     |

## The trap

Plausible but wrong

A growing if-else chain where adding one vehicle type breaks another.

The "before" method starts with the auto's numbers as defaults and overrides them per branch. Cab XL was added by raising a default, since XL "uses the defaults". The first test shows the result: a 10 km auto ride now costs ₹190 instead of ₹150. The second test asks the real rules: each type has its own, so XL's numbers cannot reach the auto. Removing the "never below zero" guard from the auto meter was tried while building: 2 tests went red.

``` code
package com.rydo.fares;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The "before" fare code is one method with an if-else chain. CAB_XL was added last.
 */
class IfElseChainTrapTest {

    /** Kept only in tests. The defaults at the top were the auto's numbers; whatever no branch catches is priced as an auto. */
    static double oldFare(String type, double km) {
        double base = 30, perKm = 20, freeKm = 2;   // perKm was 15; raised to 20 "for CAB_XL", which uses the defaults
        if (type.equals("BIKE")) {
            base = 20; perKm = 6; freeKm = 0;
        } else if (type.equals("CAB")) {
            base = 50; perKm = 14; freeKm = 0;
        } else if (type.equals("CAB_XL")) {
            base = 80; freeKm = 0;                   // perKm comes from the default above
        }
        return base + perKm * Math.max(0, km - freeKm);
    }

    @Test
    void addingCabXlChangedTheAutoFareThatNobodyTouched() {
        assertThat(oldFare("AUTO", 10)).isEqualTo(190.0);  // the auto meter says 30 + 8 x 15 = 150
        assertThat(oldFare("CAB_XL", 10)).isEqualTo(280.0);
    }

    @Test
    void withARulePerVehicleTypeEachFareStaysItsOwn() {
        assertThat(VehicleType.AUTO.farePaise(new BigDecimal("10"))).isEqualTo(150_00);
        assertThat(VehicleType.CAB_XL.farePaise(new BigDecimal("10"))).isEqualTo(280_00);
    }

    @Test
    void doubleArithmeticIsNotExactForMoney() {
        assertThat(0.1 + 0.2).isNotEqualTo(0.3);                                          // 0.30000000000000004
        assertThat(new BigDecimal("0.1").add(new BigDecimal("0.2"))).isEqualByComparingTo("0.3");
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
./mvnw test                 # all 12 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

``` code
# MG Road to Koramangala: expect "distanceKm": 6.4
curl "http://localhost:8080/fare-estimates?pickup=12.9756,77.6066&drop=12.9352,77.6245"

# Try to set your own distance: nothing changes
curl "http://localhost:8080/fare-estimates?pickup=12.9756,77.6066&drop=12.9352,77.6245&distanceKm=1"
```

## Troubleshooting

| You see                            | Cause                                          | Fix                                                                |
|------------------------------------|------------------------------------------------|--------------------------------------------------------------------|
| Only `pickup` arrives              | The shell cut the URL at `&`.                  | Put the URL in double quotes.                                      |
| `422 Outside service area`         | The demo area is a rectangle around Bengaluru. | Use points between latitude 12.80–13.25 and longitude 77.40–77.80. |
| `release version 25 not supported` | Maven is using an older JDK.                   | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`.           |

## Project layout

``` tree
stations/014-fare-estimates-per-vehicle-type/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/rydo/fares/
│   ├── FareEstimateController.java   ├── Location.java    ├── VehicleType.java
│   ├── FareRule.java                 ├── PerKmRule.java   ├── MeterRule.java
│   └── FaresApplication.java
├── src/test/java/com/rydo/fares/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/rydo/fares/FareEstimateController.java`

Does  
Reads the two points, computes the distance, asks every vehicle type for a fare.

Why  
No vehicle is special-cased: the loop asks each one the same question.

Without it  
No API; and with a distance parameter, a client could set its own price.

#### `src/main/java/com/rydo/fares/Location.java`

Does  
Parses `lat,lng`, checks the service area, and estimates road distance.

Why  
One place for geography.

Without it  
Coordinates parsed in several places.

- Haversine gives the straight-line distance on a sphere; × 1.3 is a demo allowance for roads.

#### `src/main/java/com/rydo/fares/VehicleType.java`

Does  
An enum where each value holds its fare rule; rounds to whole rupees and returns paise.

Why  
The type and its rule live together: a new type is one line.

Without it  
The if-else chain, and its shared variables.

- Amounts are built from strings: `new BigDecimal("0.1")` is exact, `new BigDecimal(0.1)` is not.
- `longValueExact` fails loudly instead of silently cutting digits.

#### `src/main/java/com/rydo/fares/FareRule.java`

Does  
The strategy interface: distance in, rupees out.

Why  
The estimator depends only on this.

Without it  
Every caller would need to know every rule.

#### `src/main/java/com/rydo/fares/PerKmRule.java`

Base + per km, with a minimum. Used by bikes and cabs.

#### `src/main/java/com/rydo/fares/MeterRule.java`

Auto meter: the first km are included in the base.

#### `src/main/resources/application.yaml`

RFC 9457 problem bodies for every error.

#### `src/main/java/com/rydo/fares/FaresApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                     | Result |
|---------------|------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `FareEstimateContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix     | `IfElseChainTrapTest` (3)      | pass   |
| This station  | Each rule at its boundaries; rounding    | `FareRulesTest` (4)            | pass   |

The contract tests look each vehicle up by name instead of checking the exact list. A test that lists every vehicle type would itself break whenever a type is added: the same closed-to-extension mistake as the if-else chain.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.rydo.fares.FareRulesTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.rydo.fares.FareEstimateContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.rydo.fares.IfElseChainTrapTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/rydo/fares/IfElseChainTrapTest.java`

Written first: the shared default that moved the auto fare; `double` against `BigDecimal`.

#### `src/test/java/com/rydo/fares/FareEstimateContractTest.java`

Real coordinates, minimums, ignored price inputs, refusals.

#### `src/test/java/com/rydo/fares/FareRulesTest.java`

Each rule at its boundaries; half-up rounding; the distance.

#### `src/test/java/com/rydo/fares/ApiTest.java`

Shared setup: the whole app through MockMvc.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/rydo/fares/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=EvCabChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (12 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 15 minutes

## Launch EV cabs

Add `EV_CAB`: ₹50 base, ₹12 per km, ₹80 minimum. Every other fare must stay exactly the same.

**Done when:** `EvCabChallengeTest` passes, and the station's tests still pass.

Hints

- One new enum value with a `PerKmRule`. If you find yourself editing anything else, stop and ask why.

#### `challenge/EvCabChallengeTest.java`

``` code
package com.rydo.fares;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 1: Rydo launches EV_CAB: Rs 50 base, Rs 12 per km, Rs 80 minimum. No other fare may change. */
class EvCabChallengeTest extends ApiTest {

    @Test
    void evCabsAreEstimatedAndNothingElseMoves() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", "12.9756,77.6066").param("drop", "12.9352,77.6245"))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'EV_CAB')].farePaise", contains(12700)))   // 126.80 -> 127
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'AUTO')].farePaise", contains(9600)))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'CAB')].farePaise", contains(14000)));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Airport toll

Trips that end at the airport (a demo box: latitude 13.18–13.22, longitude 77.68–77.73) add a ₹120 toll for cars; bikes and autos do not pay it.

**Done when:** both tests in `AirportTollChallengeTest` pass.

Hints

- Whether a vehicle pays tolls is a fact about the vehicle type: put it on the enum.
- Whether a trip ends at the airport is a fact about the location: put it on `Location`.
- Add the toll in paise after rounding the fare, so it is never rounded.

#### `challenge/AirportTollChallengeTest.java`

``` code
package com.rydo.fares;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: trips to the airport (latitude 13.18 to 13.22, longitude 77.68 to 77.73, a demo box) pay a Rs 120
 * toll in cars, not on bikes or autos.
 */
class AirportTollChallengeTest extends ApiTest {

    static final String MG_ROAD = "12.9756,77.6066", AIRPORT = "13.1986,77.7066";

    @Test
    void carsToTheAirportPayTheTollBikesAndAutosDoNot() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", MG_ROAD).param("drop", AIRPORT))
                .andExpect(jsonPath("$.distanceKm").value(35.2))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'CAB')].farePaise", contains(54300 + 12000)))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'CAB_XL')].farePaise", contains(78400 + 12000)))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'AUTO')].farePaise", contains(52800)))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'BIKE')].farePaise", contains(23100)));
    }

    @Test
    void tripsElsewhereHaveNoToll() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", MG_ROAD).param("drop", "12.9352,77.6245"))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'CAB')].farePaise", contains(14000)));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Night fares and surge

Autos charge 1.5× between 11 p.m. and 5 a.m., and cabs may have a demand multiplier. Sketch both as rules that wrap another rule (a decorator). In which order do you apply night fare, surge and the minimum? Where does "now" come from, and how do you test 10:59 p.m. and 11:00 p.m.?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the shared default moves the auto fare.
2.  Write the `FareRule` interface and the two rule shapes (per km, meter).
3.  Give each vehicle type its rule on the enum.
4.  Compute distance on the server; round fares with an explicit mode; return paise.
5.  Test each rule at its boundaries, independently of HTTP.

## Design alternatives and trade-offs

| Approach                                      | What it costs                                                         | Verdict       |
|-----------------------------------------------|-----------------------------------------------------------------------|---------------|
| Strategy objects held by an enum              | A small interface and one record per rule shape.                      | Chosen        |
| One method with if-else or switch on a string | Shared variables; every change touches every type (the trap).         | Wrong         |
| A subclass per vehicle type                   | Works for this, but inheritance is heavier than needed (station 012). | Possible      |
| Rates in configuration or a database          | Change prices without a release; needs validation and an audit trail. | In production |
| `double` for money                            | 0.1 + 0.2 ≠ 0.3; rounding errors add up across millions of rides.     | Wrong         |

## Database design

None. In production, rates would be dated rows (vehicle type, base, per km, minimum, valid from), so a change takes effect at a set time and old receipts can still be explained.

# 3 · Go deeper: Production

Security  
Prices come only from server-side inputs: coordinates are validated, the area is checked, the distance is the server's. The final fare at the end of a real ride would be computed again from the trip's own data.

Money  
Exact decimals, one explicit rounding step, whole rupees in paise. Show riders the distance the fare was computed from.

Maintainability  
A new vehicle type is one line; tests look types up by name, so they do not break either.

Accuracy  
Straight-line × 1.3 is a demo; real estimates use routing and traffic, and are labelled "estimate".

# 3 · Go deeper: Interview

## Interview takeaways

What is the strategy pattern?

Each way of doing a job is its own object behind a shared interface; the caller holds one and calls it without knowing which. New behaviour means a new strategy, not edits to existing ones.

What is the open/closed principle?

Code should be open for extension and closed for modification: add a vehicle type by adding code, without changing code that already works and is tested.

Why not double for money?

double is binary floating point and cannot represent most decimal fractions exactly (0.1 + 0.2 = 0.30000000000000004). Use BigDecimal (built from strings) or whole minor units.

How do you round money in Java?

setScale with an explicit RoundingMode, once, at a documented step. Never let a library pick a default.

Why compute the distance on the server?

Anything that sets a price must not come from the client, which can be modified. The client sends facts (coordinates); the server derives the price.

## Self-check rubric

| Area        | Meets the bar                                  | Above the bar                                                   |
|-------------|------------------------------------------------|-----------------------------------------------------------------|
| Correctness | All 12 tests pass.                             | You can work out the fare for any distance by hand.             |
| Design      | One rule per vehicle type.                     | You can add night fares as a decorator on paper.                |
| Money       | BigDecimal and one rounding step.              | You can explain why the fare uses the rounded distance.         |
| Explanation | Strategy and open/closed in one sentence each. | You can name the shared-variable bug in someone else's if-else. |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on pricing code:

- Does adding a type mean editing a shared method?
- Is any money a `double`, or a `BigDecimal` built from a `double`?
- Is rounding explicit, and done once?
- Can any input that affects the price come from the client?
