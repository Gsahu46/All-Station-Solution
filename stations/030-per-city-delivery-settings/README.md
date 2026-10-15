# Station 030 · Per-city delivery settings

Foundations · 0–1 years · Core · Quick commerce · Types: none

Spring Boot 4.1.1 · Java 25 · @ConfigurationProperties records · @Validated · profiles · relaxed binding · @AutoConfiguration · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Delivery terms are demo values, not Basketo's. A delivery check only answers whether an order could be delivered; no order is placed. Distances are straight-line, computed on the server.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 14 tests.

# 1 · Understand

## The problem in real life

1.  **A config change goes out**

    Someone edits Pune's settings and types `minimun-order-paise`. The app starts, as always.

2.  **Nothing fails, and that is the problem**

    The real key is now missing, so the minimum order is 0. Customers in Pune order a single ₹10 lemon with free-feeling delivery, and every order loses money. Meanwhile the app also trusts the distance the phone sends.

3.  **The fix**

    Bind settings into a validated record that refuses unknown keys, missing values and impossible numbers at startup, and compute distance on the server from the address.

A bad setting should stop the deployment, not reach a customer.

## What are we building?

`GET /cities/{city}/delivery-terms` shows a city's radius, fee and minimum order. `POST /delivery-checks` says whether an address and an order amount can be delivered, with the distance the server computed.

## An everyday analogy

A restaurant's opening checklist: if the gas reading is missing or impossible, the kitchen does not open. It does not open and hope the reading was fine.

## How it works in 4 steps

1.  **At startup**, Spring binds `basketo.cities.*` into records, with profile and environment overrides applied.
2.  **It validates them**: unknown keys, missing values, a radius over 15 km or a minimum under ₹99 stop the start, naming the property.
3.  **A check arrives** with coordinates; the server computes the distance from the city's store.
4.  **It answers** with the distance, the fee, and any reasons it cannot deliver.

Check yourself: why use `Long` instead of `long` for the minimum order?

A missing `long` silently becomes 0. A missing `Long` is `null`, which `@NotNull` refuses, so a misspelt key is caught at startup.

## What this station is not

- **No road distances.** Straight-line distance; a road service could replace it.
- **No live config changes.** Settings are read at startup; challenge 3 discusses changes without a restart.
- **No orders.** A check only.

## Key terms

| Term                              | Simple meaning                                                       | Everyday example                                   | In this project                |
|-----------------------------------|----------------------------------------------------------------------|----------------------------------------------------|--------------------------------|
| **Configuration**                 | Values the app reads at startup instead of having them in code.      | A shop's price list on the wall.                   | `application.yaml`             |
| **Configuration properties**      | A Java record that Spring fills from configuration.                  | A form filled from the price list.                 | `DeliverySettings`             |
| **Fail fast**                     | Refuse to start when something is wrong, instead of running wrong.   | A pilot's checklist before take-off.               | `@Validated`                   |
| **Profile**                       | A named set of extra configuration for one environment.              | A weekend menu on top of the usual one.            | `application-dev.yaml`         |
| **Environment variable override** | A value set outside the app that replaces one in the file.           | A sticky note over one price.                      | `BASKETO_CITIES_PUNE_FEEPAISE` |
| **Auto-configuration**            | A default bean Spring Boot adds only if you have not added your own. | A spare key, used only if you did not bring yours. | `DistanceAutoConfiguration`    |

# 2 · Build: Spec

## Business problem

**Basketo** (a fictional quick-commerce app) sets a delivery radius, fee and minimum order per city. A typo in a config key once set a minimum order to ₹0 and nothing failed. The delivery check also used the distance the app sent, so a modified client could get delivery anywhere.

## Acceptance criteria

1.  **Given** a misspelt key, a missing value, a minimum below ₹99 or a radius over 15 km, **then** the app does not start, and the error names the property.
2.  **Given** an extra key nobody reads, **then** the app does not start.
3.  **Given** `BASKETO_CITIES_PUNE_FEEPAISE=3000`, **then** Pune's fee is ₹30 and its other values come from the file.
4.  **Given** the `dev` profile, **then** a test city exists; without it, it does not.
5.  **Given** an address in Koregaon Park, **then** 4.94 km from the Pune store, deliverable; Hinjewadi at 13.28 km with ₹99 is not, for two reasons.
6.  **Given** a `distanceKm` in the request, **then** `400`; an unknown city, `404`.

## Requirements

- Demo limits: radius 0.5 to 15 km; fee ₹0 to ₹100; minimum order at least ₹99.
- Settings are records with wrapper types and validation; unknown keys are an error.
- Distance is computed on the server (haversine, mean Earth radius 6,371.0088 km).
- City names are normalised with `Locale.ROOT`.

## Learning objectives

- Bind configuration into records with `@ConfigurationProperties`.
- Make configuration fail fast with `@Validated` and `ignoreUnknownFields = false`.
- Use profiles and environment variable overrides.
- Explain auto-configuration and `@ConditionalOnMissingBean`.
- Compute on the server what the client could lie about.

# 2 · Build: API contract

## Endpoints

| Method | Path                            | Purpose                                                                     |
|--------|---------------------------------|-----------------------------------------------------------------------------|
| `GET`  | `/cities/{city}/delivery-terms` | Radius, fee and minimum order for a city.                                   |
| `POST` | `/delivery-checks`              | `{"city", "lat", "lon", "orderPaise"}`: can this be delivered, and why not? |

## Status codes

| Status | When                                                                                |
|--------|-------------------------------------------------------------------------------------|
| 200    | Terms; a check (deliverable or not, with reasons)                                   |
| 400    | Coordinates out of range, a missing field, a fraction of a paisa, or a `distanceKm` |
| 404    | A city Basketo does not serve                                                       |

## Captured examples

Captured with curl from the running app on 15 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Pune's terms

**Why:** straight from the validated settings.

Request

``` code
GET /cities/pune/delivery-terms HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 72

{
  "city": "pune",
  "radiusKm": 6.0,
  "feePaise": 2500,
  "minimumOrderPaise": 14900
}
```

### Case 2: Koregaon Park, ₹250

**Why:** 4.94 km from the store, inside 6 km, above ₹149: deliverable.

Request

``` code
POST /delivery-checks HTTP/1.1
Content-Type: application/json

{
  "city": "pune",
  "lat": 18.5362,
  "lon": 73.894,
  "orderPaise": 25000
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 126

{
  "city": "pune",
  "distanceKm": 4.94,
  "deliverable": true,
  "reasons": [],
  "feePaise": 2500,
  "minimumOrderPaise": 14900,
  "orderPaise": 25000
}
```

### Case 3: Hinjewadi, ₹99

**Why:** 13.28 km and below the minimum: both reasons, so the app can say both.

Request

``` code
POST /delivery-checks HTTP/1.1
Content-Type: application/json

{
  "city": "pune",
  "lat": 18.5913,
  "lon": 73.7389,
  "orderPaise": 9900
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 157

{
  "city": "pune",
  "distanceKm": 13.28,
  "deliverable": false,
  "reasons": [
    "OUT_OF_RANGE",
    "BELOW_MINIMUM"
  ],
  "feePaise": 2500,
  "minimumOrderPaise": 14900,
  "orderPaise": 9900
}
```

### Case 4: the app sends "distanceKm": 0

**Why:** not a field any more: `400`, so a client cannot keep believing its own number is used.

Request

``` code
POST /delivery-checks HTTP/1.1
Content-Type: application/json

{
  "city": "pune",
  "lat": 18.5913,
  "lon": 73.7389,
  "orderPaise": 25000,
  "distanceKm": 0
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/delivery-checks",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: Jaipur

**Why:** `404`.

Request

``` code
GET /cities/jaipur/delivery-terms HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "Basketo does not deliver in this city yet.",
  "instance": "/cities/jaipur/delivery-terms",
  "status": 404,
  "title": "City not served"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                     | What happens                                | Proved by                                               |
|----------------------------------------------------------|---------------------------------------------|---------------------------------------------------------|
| Minimum 0; radius 60; minimum missing                    | The app does not start                      | `invalidValuesStopTheAppStartingAndNameTheProperty`     |
| An extra misspelt key                                    | The app does not start                      | `aMisspeltExtraKeyStopsTheAppStartingToo`               |
| An environment variable for one value                    | That value replaced, the rest from the file | `anEnvironmentVariableOverridesOneValue`                |
| The dev profile                                          | A test city appears                         | `theDevProfileAddsATestCity`                            |
| Your own `DistanceCalculator` bean                       | The default steps aside                     | `aBeanOfYourOwnReplacesTheDefaultCalculator`            |
| Pune to Mumbai                                           | 120.15 km straight-line                     | `straightLineDistanceMatchesAKnownOne`                  |
| Terms; in range; out of range and too small              | As specified                                | `DeliveryContractTest`                                  |
| A client-sent distance                                   | `400`                                       | `theServerSaysTooFarAndTooSmallWhateverTheClientThinks` |
| Jaipur                                                   | `404`                                       | `aCityWeDoNotServeIs404`                                |
| Latitude 91; zero or fractional amounts; a missing field | `400`                                       | `badCoordinatesOrAmountsAre400`                         |

## The trap

Plausible but wrong

Unvalidated config: a typo sets the minimum order to zero and nothing fails.

The first test binds the old settings (primitives, no validation) with the typo: the app starts and Pune's minimum is 0. The second binds the real settings with the same typo: the start fails, naming `cities[pune].minimumOrderPaise` as null. The third shows the old check believing a client's 0 km. While building, removing `@Validated` turned 2 tests red, and allowing unknown keys turned 1 red.

``` code
package com.basketo.delivery;

import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.autoconfigure.context.ConfigurationPropertiesAutoConfiguration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: it reproduces the bugs before the fix. */
class UnvalidatedConfigTrapTest {

    /** The "before" settings: primitives, no validation, unknown keys ignored. Kept only in tests. */
    @ConfigurationProperties("basketo")
    record OldSettings(Map<String, OldCity> cities) {
        record OldCity(double radiusKm, long feePaise, long minimumOrderPaise) {
        }
    }

    @Configuration
    @EnableConfigurationProperties(OldSettings.class)
    static class OldApp {
    }

    /** The "before" check: the client said how far it was. Kept only in tests. */
    static boolean oldDeliverable(double clientDistanceKm, double radiusKm) {
        return clientDistanceKm <= radiusKm;
    }

    @Test
    void theOldSettingsStartWithAMisspeltKeyAndAMinimumOfZero() {
        new ApplicationContextRunner()
                .withConfiguration(AutoConfigurations.of(ConfigurationPropertiesAutoConfiguration.class))
                .withUserConfiguration(OldApp.class)
                .withPropertyValues("basketo.cities.pune.radius-km=6.0", "basketo.cities.pune.fee-paise=2500",
                        "basketo.cities.pune.minimun-order-paise=14900")   // "minimun": one letter wrong
                .run(context -> {
                    assertThat(context).hasNotFailed();
                    assertThat(context.getBean(OldSettings.class).cities().get("pune").minimumOrderPaise()).isZero();
                });
    }

    @Test
    void theRealSettingsRefuseToStartWithThatTypo() {
        ConfigRunner.settings("basketo.cities.pune.minimun-order-paise=14900")
                // the real key is now missing: a Long, not a long, so it is null, and @NotNull stops the start
                .run(context -> assertThat(context).hasFailed().getFailure()
                        .hasStackTraceContaining("cities[pune].minimumOrderPaise").hasStackTraceContaining("rejected value [null]"));
    }

    @Test
    void theOldCheckBelievesWhateverDistanceTheClientSends() {
        assertThat(oldDeliverable(0.0, 6.0)).isTrue();   // an address 13 km away, "0 km" according to the app
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
./mvnw spring-boot:run                                         # the API on http://localhost:8080
./mvnw spring-boot:run -Dspring-boot.run.profiles=dev          # with the dev profile's test city
BASKETO_CITIES_PUNE_FEEPAISE=3000 ./mvnw spring-boot:run       # one value overridden
./mvnw test                                                    # all 14 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
$env:BASKETO_CITIES_PUNE_FEEPAISE = "3000"; .\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Break the configuration on purpose: change `minimum-order-paise` to `minimun-order-paise` in `application.yaml` and start the app. It refuses, naming the property. Put it back.

``` code
curl -X POST http://localhost:8080/delivery-checks -H "Content-Type: application/json" \
     -d '{"city":"pune","lat":18.5362,"lon":73.8940,"orderPaise":25000}'
```

## Troubleshooting

| You see                                           | Cause                               | Fix                                                                                                     |
|---------------------------------------------------|-------------------------------------|---------------------------------------------------------------------------------------------------------|
| `Binding validation errors on basketo` at startup | A value is missing or out of range. | Read the field it names, and fix that line.                                                             |
| `Could not bind properties to 'DeliverySettings'` | An unknown key, often a typo.       | Check the spelling of each key under `basketo.cities`.                                                  |
| An environment variable has no effect             | The name does not map to the key.   | Upper case, dots and dashes removed: `basketo.cities.pune.fee-paise` is `BASKETO_CITIES_PUNE_FEEPAISE`. |

## Project layout

``` tree
stations/030-per-city-delivery-settings/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/basketo/delivery/
│   ├── DeliveryController.java   ├── DeliverySettings.java
│   ├── DistanceCalculator.java   ├── DistanceAutoConfiguration.java   └── DeliveryApplication.java
├── src/main/resources/
│   ├── application.yaml   ├── application-dev.yaml
│   └── META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
├── src/test/java/com/basketo/delivery/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the configuration behind it.

#### `src/main/java/com/basketo/delivery/DeliveryController.java`

Does  
Finds the city's settings and runs the check with the server's own distance.

Why  
No distance in the request at all: there is nothing for a client to lie about.

Without it  
Trusting a `distanceKm` from the app.

#### `src/main/java/com/basketo/delivery/DeliverySettings.java`

Does  
The settings as validated records.

Why  
Wrapper types, constraints and `ignoreUnknownFields = false`: every bad setting stops the start.

Without it  
The trap: primitives that default to 0, and no checks.

- `@Validated` runs Bean Validation on the bound record at startup.
- `@Valid` on the map values and the store location checks the nested records too.

#### `src/main/java/com/basketo/delivery/DistanceAutoConfiguration.java`

Does  
The default distance calculator, as an auto-configuration.

Why  
Listed in `META-INF/spring/…AutoConfiguration.imports`, so it runs after the app's own beans and `@ConditionalOnMissingBean` can see them.

Without it  
The same condition on an ordinary `@Configuration`: its result depends on the order definitions are processed. Spring Boot's documentation recommends the condition only on auto-configuration classes.

#### `src/main/java/com/basketo/delivery/DistanceCalculator.java`

The one-method interface any distance source implements.

#### `src/main/resources/application.yaml`

The demo cities, strict JSON, and a note on environment overrides.

#### `src/main/resources/application-dev.yaml`

The `dev` profile: a test city for testers.

#### `src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`

Registers the auto-configuration.

#### `src/main/java/com/basketo/delivery/DeliveryApplication.java`

Entry point; `@ConfigurationPropertiesScan` finds the settings record.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                     | Test class                      | Result |
|---------------|-----------------------------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                        | `DeliveryContractTest` (5)      | pass   |
| Every station | Reproduce the failure before the fix                            | `UnvalidatedConfigTrapTest` (3) | pass   |
| This station  | Validation, environment, profiles, auto-configuration, distance | `DeliveryConfigTest` (6)        | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.delivery.UnvalidatedConfigTrapTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.delivery.DeliveryConfigTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.basketo.delivery.DeliveryContractTest
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/basketo/delivery/UnvalidatedConfigTrapTest.java`

Written first: the old settings start with a typo; the real ones refuse.

#### `src/test/java/com/basketo/delivery/DeliveryConfigTest.java`

Startup failures, an environment variable, the dev profile, a replaced default, and a known distance.

#### `src/test/java/com/basketo/delivery/DeliveryContractTest.java`

Terms and checks through HTTP, and every refusal.

#### `src/test/java/com/basketo/delivery/ConfigRunner.java`

A tiny context with only the settings, binding and validation: fails or starts in milliseconds.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/basketo/delivery/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=FreeDeliveryChallengeTest` (the app refuses the new key until you add it).
3.  Change the code until it passes, then run `./mvnw test` to check the other 14 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 18 tests pass (14 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Free delivery above a threshold

Add an optional `free-delivery-above-paise` per city. Orders at or above it pay no fee. It must be above the city's minimum order, or the app does not start.

**Done when:** both tests in `FreeDeliveryChallengeTest` pass.

Hints

- An optional `Long`: `null` means no threshold.
- A rule across two fields: an `@AssertTrue` method named `isSomething()` on the record.

#### `challenge/FreeDeliveryChallengeTest.java`

``` code
package com.basketo.delivery;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: an optional basketo.cities.*.free-delivery-above-paise. Orders at or above it pay no fee. It must be
 * above the city's minimum order, or the app does not start (a rule across two fields).
 */
@SpringBootTest(properties = "basketo.cities.pune.free-delivery-above-paise=49900")
@AutoConfigureMockMvc
class FreeDeliveryChallengeTest {

    @Autowired
    MockMvc mvc;

    @Test
    void bigOrdersDeliverFree() throws Exception {
        String at = "{\"city\":\"pune\",\"lat\":18.5362,\"lon\":73.8940,\"orderPaise\":%d}";
        mvc.perform(post("/delivery-checks").contentType(MediaType.APPLICATION_JSON).content(at.formatted(49_900)))
                .andExpect(jsonPath("$.feePaise").value(0));
        mvc.perform(post("/delivery-checks").contentType(MediaType.APPLICATION_JSON).content(at.formatted(30_000)))
                .andExpect(jsonPath("$.feePaise").value(2500));
    }

    @Test
    void aThresholdBelowTheMinimumOrderStopsTheAppStarting() {
        ConfigRunner.settings("basketo.cities.pune.minimum-order-paise=14900", "basketo.cities.pune.free-delivery-above-paise=10000")
                .run(c -> assertThat(c).hasFailed().getFailure().hasStackTraceContaining("freeDeliveryAboveMinimum"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Fees by distance band

Add optional `fee-bands` per city (up to 3 km ₹15, up to 6 km ₹30, …) that replace the flat fee. Bands must increase and the last must reach the radius, or the app does not start.

**Done when:** both tests in `DistanceBandsChallengeTest` pass, and the station's tests still pass.

Hints

- A list of records binds from `fee-bands[0].up-to-km` and so on.
- The fee uses the server's distance: the first band whose limit is not below it.

#### `challenge/DistanceBandsChallengeTest.java`

``` code
package com.basketo.delivery;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: optional fee bands per city, replacing the flat fee: up to 3 km Rs 15, up to 6 km Rs 30. Bands must be
 * in increasing distance and the last must reach the city's radius, or the app does not start.
 */
@SpringBootTest(properties = {
        "basketo.cities.pune.fee-bands[0].up-to-km=3.0", "basketo.cities.pune.fee-bands[0].fee-paise=1500",
        "basketo.cities.pune.fee-bands[1].up-to-km=6.0", "basketo.cities.pune.fee-bands[1].fee-paise=3000"})
@AutoConfigureMockMvc
class DistanceBandsChallengeTest {

    @Autowired
    MockMvc mvc;

    @Test
    void theFeeDependsOnTheServersDistance() throws Exception {
        String at = "{\"city\":\"pune\",\"lat\":%s,\"lon\":%s,\"orderPaise\":25000}";
        mvc.perform(post("/delivery-checks").contentType(MediaType.APPLICATION_JSON).content(at.formatted("18.5362", "73.8940")))   // 4.94 km
                .andExpect(jsonPath("$.feePaise").value(3000));
        mvc.perform(post("/delivery-checks").contentType(MediaType.APPLICATION_JSON).content(at.formatted("18.5308", "73.8575")))   // about 1 km
                .andExpect(jsonPath("$.feePaise").value(1500));
    }

    @Test
    void bandsThatStopShortOfTheRadiusStopTheAppStarting() {
        ConfigRunner.settings("basketo.cities.pune.minimum-order-paise=14900",
                        "basketo.cities.pune.fee-bands[0].up-to-km=3.0", "basketo.cities.pune.fee-bands[0].fee-paise=1500")
                .run(c -> assertThat(c).hasFailed().getFailure().hasStackTraceContaining("feeBandsCoverTheRadius"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Changing settings without a restart

Operations wants to raise Mumbai's fee during heavy rain, in minutes. Compare a restart with new environment variables, a settings table in the database, and a config server. How does each one keep the fail-fast checks of this station, and what does a customer see while the change rolls out?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old settings start with a typo and a zero minimum.
2.  Write the settings as records with wrapper types and constraints; refuse unknown keys.
3.  Test startup failures in small contexts; test profiles and environment overrides on the real app.
4.  Move the distance into the server, behind a replaceable default.

## Design alternatives and trade-offs

| Approach                                     | What it costs                                                                   | Verdict               |
|----------------------------------------------|---------------------------------------------------------------------------------|-----------------------|
| Validated `@ConfigurationProperties` records | A record and its constraints.                                                   | Chosen                |
| `@Value` on each field                       | No validation in one place; typos become defaults or startup errors one by one. | For one or two values |
| Primitives and no validation                 | A missing value becomes 0.                                                      | The trap              |
| Ignoring unknown keys                        | A misspelt extra key is silently ignored.                                       | Hides typos           |
| The client's distance                        | Any client can claim 0 km.                                                      | Never                 |

## Database design

None in this station. If settings move to a table: `city_delivery_terms` with check constraints mirroring the record's (radius between 0.5 and 15, minimum at least 9900), so a bad row is refused by the database too.

# 3 · Go deeper: Production

Deployments  
A bad setting now fails the deployment's startup, so the old version keeps serving. That is the point: the error reaches an engineer, not a customer.

Secrets and environments  
Per-environment values come from environment variables or a secret store, never committed. Profiles hold whole sets of differences (dev, staging).

Trust  
Anything the client could change (distance, price, discount) is computed or looked up on the server.

Distance  
Straight-line distance is always shorter than the road. A real radius check may use a routing service, plugged in as its own `DistanceCalculator`.

# 3 · Go deeper: Interview

## Interview takeaways

How do you make Spring Boot configuration fail fast?

Bind it into a @ConfigurationProperties class or record, add @Validated with Bean Validation constraints, use wrapper types so missing values are null, and set ignoreUnknownFields = false so typos are errors.

How does an environment variable override a property?

Relaxed binding: upper case, dots to underscores, dashes removed. basketo.cities.pune.fee-paise becomes BASKETO_CITIES_PUNE_FEEPAISE, and it wins over application.yaml.

What is a profile?

A named set of configuration (application-dev.yaml) applied on top of the defaults when the profile is active.

What is auto-configuration?

Configuration classes Spring Boot applies after your own beans, usually with conditions like @ConditionalOnMissingBean, so they supply sensible defaults you can replace by defining your own bean.

Why compute the distance on the server?

The client controls everything it sends. A value that decides price or eligibility must come from data the server trusts.

## Self-check rubric

| Area          | Meets the bar                       | Above the bar                                                  |
|---------------|-------------------------------------|----------------------------------------------------------------|
| Correctness   | All 14 tests pass.                  | You broke the config on purpose and read the error.            |
| Configuration | Validated records, no unknown keys. | You can map any property to its environment variable.          |
| Spring Boot   | Profiles and overrides.             | Why `@ConditionalOnMissingBean` belongs on auto-configuration. |
| Explanation   | Why `Long`, not `long`.             | What the server must never take from the client.               |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any configuration change:

- Does a typo in a key stop the app, or quietly change a value?
- Which values have limits, and are they checked at startup?
- Are environment-specific values outside the repository?
- Does any setting depend on something the client sends?
