# Station 029 · Travel insurance premium factors

Foundations · 0–1 years · Core · Insurance · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · List injection · @Order · @Qualifier · @Primary · @PostConstruct · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** A quote only: no policy is issued and nothing is charged. The rates are demo numbers, not a real insurer's, and taxes are not included.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **One giant premium class**

    Every new risk (a new destination, a new age band, adventure sports) means editing the same 400-line class. Every edit risks every price.

2.  **A first split goes wrong**

    Factors become separate beans, but the quote service asks for one `PremiumFactor`. The app will not start; someone adds `@Primary`, and it starts, quoting with one factor. Then the order of the factors depends on how classes were scanned, and the adventure loading gets multiplied by age: ₹400 too much.

3.  **The fix**

    Inject all factors as a list, in an explicit order, and refuse to start if two share an order.

When several beans do one job together, ask for all of them, and say their order out loud.

## What are we building?

`POST /premium-quotes` prices a trip by running every premium factor in order, and returns the premium with a breakdown of each step.

## An everyday analogy

A recipe: dough, then filling, then oven, then glaze. Each step is separate and numbered. Swap the oven and the glaze and you get a different dish, from the same ingredients.

## How it works in 4 steps

1.  **At startup**, Spring collects every `PremiumFactor` bean, sorted by `@Order`, and the calculator checks no two share a place.
2.  **For each quote**, the running total starts at zero.
3.  **Each factor** takes the total and returns a new one, with a line for the breakdown.
4.  **Finally**, the premium is rounded up to the rupee (the insurer's rule) and the per-day figure to the nearest rupee.

Check yourself: the adventure add-on is ₹50 a day. Why does it matter whether it comes before or after the age multiplier?

After, it stays ₹50 a day. Before, it is multiplied too: ×1.8 for a 67-year-old, ₹90 a day. Same factors, different price, so the order is part of the rule.

## What this station is not

- **Not real insurance pricing.** Demo rates; real pricing is regulated and actuarial.
- **No policy.** A quote only.
- **No taxes.** The premium shown excludes them.

## Key terms

| Term                        | Simple meaning                                                        | Everyday example                                    | In this project       |
|-----------------------------|-----------------------------------------------------------------------|-----------------------------------------------------|-----------------------|
| **Premium**                 | What a traveller pays for the policy.                                 | ₹1,839 for 10 days in Europe.                       | `premiumPaise`        |
| **Factor**                  | One step that changes the premium: a rate, a multiplier or an add-on. | Age, destination, adventure sports.                 | `PremiumFactor`       |
| **Bean**                    | An object Spring creates and hands to whoever needs it.               | A tool in a shared workshop, given to whoever asks. | Each factor is a bean |
| **List injection**          | Asking Spring for every bean of a type, as a list.                    | Asking for "all the checklists", not one.           | `List<PremiumFactor>` |
| **@Order**                  | The position of a bean in such a list.                                | Step numbers on a recipe.                           | `@Order(30)` on `Age` |
| **@Qualifier and @Primary** | Picking one bean when there are several: by name, or the default.     | "The red pen" versus "a pen".                       | Two `Rounding` beans  |

# 2 · Build: Spec

## Business problem

**Bimaly** (a fictional insurance app) adds risk factors often. In one class, each change risks every price; split carelessly into beans, the app either fails to start, quotes with one factor, or applies factors in whatever order classes happen to load.

## Acceptance criteria

1.  **Given** age 67, Europe, 10 days, adventure sports, **then** ₹1,838.75 before rounding, charged as ₹1,839, with base, destination, age, adventure and minimum in that order.
2.  **Given** age 25, Asia, 3 days, **then** the ₹199 minimum.
3.  **Given** age 45, Europe, 5 days, **then** ₹483.44 is charged as ₹484: rounded up, never to the nearest.
4.  **Given** age 81, **then** `422`: online quotes go up to 80 (a demo rule).
5.  **Given** an unknown destination, days outside 1 to 180, or no age, **then** `400`.
6.  **Given** two factors with the same `@Order`, or one with none, **then** the app does not start.

## Requirements

- Demo rates: ₹42.50 a day; destination ×1.00 to ×3.00; age ×0.80 to ×2.50; adventure +₹50 a day, not multiplied; minimum ₹199.
- Each step rounds to the paisa; the premium rounds up to the rupee; the per-day figure to the nearest rupee.
- Factors are stateless singletons; a new factor is a new bean with an `@Order`.
- `adventureSports` is optional (false when missing).

## Learning objectives

- Inject several beans of one type as a `List`, in a defined order.
- Choose one bean among several with `@Qualifier`, and a default with `@Primary`.
- Know why factors must be stateless singletons.
- Use a lifecycle callback (`@PostConstruct`) to fail fast at startup.

# 2 · Build: API contract

## Endpoint

| Method | Path              | Purpose                                    |
|--------|-------------------|--------------------------------------------|
| `POST` | `/premium-quotes` | A premium with its step-by-step breakdown. |

## Request body

| Field             | Rule                                           |
|-------------------|------------------------------------------------|
| `age`             | 0 to 120; above 80 is `422`.                   |
| `destination`     | `ASIA`, `EUROPE`, `USA_CANADA` or `WORLDWIDE`. |
| `days`            | 1 to 180.                                      |
| `adventureSports` | Optional, default false.                       |

## Status codes

| Status | When                                                   |
|--------|--------------------------------------------------------|
| 200    | A quote                                                |
| 400    | A field missing, out of range or not one of the values |
| 422    | Over 80: no online cover                               |

## Captured examples

Captured with curl from the running app on 14 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: 67, Europe, 10 days, adventure sports

**Why:** each step in order: base ₹425, Europe ×1.75, age ×1.80, then the adventure add-on, not multiplied. ₹1,838.75 is charged as ₹1,839.

Request

``` code
POST /premium-quotes HTTP/1.1
Content-Type: application/json

{
  "age": 67,
  "destination": "EUROPE",
  "days": 10,
  "adventureSports": true
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 413

{
  "premiumPaise": 183900,
  "perDayPaise": 18400,
  "breakdown": [
    {
      "factor": "base",
      "note": "10 days at Rs 42.50",
      "totalPaise": 42500
    },
    {
      "factor": "destination",
      "note": "EUROPE x 1.75",
      "totalPaise": 74375
    },
    {
      "factor": "age",
      "note": "age 67 x 1.80",
      "totalPaise": 133875
    },
    {
      "factor": "adventure",
      "note": "adventure sports, Rs 50.00 a day",
      "totalPaise": 183875
    },
    {
      "factor": "minimum",
      "note": "above the Rs 199.00 minimum",
      "totalPaise": 183875
    }
  ]
}
```

### Case 2: 25, Asia, 3 days

**Why:** ₹127.50 of cover is raised to the ₹199 minimum.

Request

``` code
POST /premium-quotes HTTP/1.1
Content-Type: application/json

{
  "age": 25,
  "destination": "ASIA",
  "days": 3
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 396

{
  "premiumPaise": 19900,
  "perDayPaise": 6600,
  "breakdown": [
    {
      "factor": "base",
      "note": "3 days at Rs 42.50",
      "totalPaise": 12750
    },
    {
      "factor": "destination",
      "note": "ASIA x 1.00",
      "totalPaise": 12750
    },
    {
      "factor": "age",
      "note": "age 25 x 1.00",
      "totalPaise": 12750
    },
    {
      "factor": "adventure",
      "note": "no adventure sports",
      "totalPaise": 12750
    },
    {
      "factor": "minimum",
      "note": "raised to the Rs 199.00 minimum",
      "totalPaise": 19900
    }
  ]
}
```

### Case 3: 45, Europe, 5 days

**Why:** ₹483.44 is charged as ₹484: the qualified rounding bean rounds up. The per-day figure uses the default (nearest).

Request

``` code
POST /premium-quotes HTTP/1.1
Content-Type: application/json

{
  "age": 45,
  "destination": "EUROPE",
  "days": 5
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 394

{
  "premiumPaise": 48400,
  "perDayPaise": 9700,
  "breakdown": [
    {
      "factor": "base",
      "note": "5 days at Rs 42.50",
      "totalPaise": 21250
    },
    {
      "factor": "destination",
      "note": "EUROPE x 1.75",
      "totalPaise": 37188
    },
    {
      "factor": "age",
      "note": "age 45 x 1.30",
      "totalPaise": 48344
    },
    {
      "factor": "adventure",
      "note": "no adventure sports",
      "totalPaise": 48344
    },
    {
      "factor": "minimum",
      "note": "above the Rs 199.00 minimum",
      "totalPaise": 48344
    }
  ]
}
```

### Case 4: age 81

**Why:** `422`: an agent quotes for older travellers.

Request

``` code
POST /premium-quotes HTTP/1.1
Content-Type: application/json

{
  "age": 81,
  "destination": "ASIA",
  "days": 3
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Online quotes cover travellers up to 80. An agent can quote for older travellers.",
  "instance": "/premium-quotes",
  "status": 422,
  "title": "No online cover for this age"
}
```

### Case 5: a destination that does not exist

**Why:** not one of the four: `400`.

Request

``` code
POST /premium-quotes HTTP/1.1
Content-Type: application/json

{
  "age": 30,
  "destination": "MARS",
  "days": 3
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/premium-quotes",
  "status": 400,
  "title": "Bad Request"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                | What happens                               | Proved by                                                  |
|-------------------------------------|--------------------------------------------|------------------------------------------------------------|
| 67, Europe, 10 days, adventure      | ₹1,839, five steps in order                | `aQuoteShowsEveryFactorInOrder`                            |
| 25, Asia, 3 days                    | ₹199 minimum                               | `aShortCheapTripPaysTheMinimum`                            |
| 106,357 and 48,344 paise            | 106,400 and 48,400: always up              | `paiseAreRoundedUpToTheNextRupee`                          |
| Age 81; age 80                      | `422`; quoted                              | `travellersOver80Are422`                                   |
| MARS; 0 or 181 days; age −1; no age | `400`                                      | `badRequestsAre400`                                        |
| The injected list                   | Base, destination, age, adventure, minimum | `theListComesInOrderOrder`                                 |
| The two rounding beans              | Qualified rounds up; primary to nearest    | `theQualifiedRoundingRoundsUpAndThePrimaryRoundsToNearest` |
| Every factor bean                   | A singleton with no per-quote fields       | `factorsAreStatelessSingletons`                            |
| Two factors with @Order(30)         | The app does not start                     | `twoFactorsWithTheSameOrderStopTheAppStarting`             |

## The trap

Plausible but wrong

Injecting one bean when several exist, or relying on unspecified bean order.

The first test builds a small context where a service asks for one `PremiumFactor` among two: it does not start. The second adds `@Primary` to one, the usual quick fix: it starts, and quotes a free policy, because only the age factor runs. The third applies the same five factors in two orders: ₹1,838.75 against ₹2,238.75. While building, removing `@Order` from one factor stopped the app (the startup check), moving adventure before age turned 2 tests red, and dropping the `@Qualifier` from the calculator turned 1 red (₹483 instead of ₹484).

``` code
package com.bimaly.premiums;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.NoUniqueBeanDefinitionException;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: it reproduces both ways the old wiring went wrong. */
class FactorOrderTrapTest {

    static final Trip SENIOR_IN_EUROPE = new Trip(67, Trip.Destination.EUROPE, 10, true);

    /** The "before" quote service: one factor, injected by type. Kept only in tests. */
    record OldQuoteService(PremiumFactor factor) {
        long quote(Trip trip) {
            return factor.apply(trip, 0).totalPaise();
        }
    }

    @Configuration
    static class TwoFactorsOneConsumer {
        @Bean
        PremiumFactor base() {
            return new Factors.Base();
        }

        @Bean
        PremiumFactor age() {
            return new Factors.Age();
        }

        @Bean
        OldQuoteService oldQuoteService(PremiumFactor factor) {
            return new OldQuoteService(factor);
        }
    }

    @Configuration
    static class SomeoneAddedPrimary {
        @Bean
        PremiumFactor base() {
            return new Factors.Base();
        }

        @Bean
        @Primary
        PremiumFactor age() {
            return new Factors.Age();
        }

        @Bean
        OldQuoteService oldQuoteService(PremiumFactor factor) {
            return new OldQuoteService(factor);
        }
    }

    static long applyInOrder(List<PremiumFactor> factors, Trip trip) {
        long total = 0;
        for (PremiumFactor f : factors) {
            total = f.apply(trip, total).totalPaise();
        }
        return total;
    }

    @Test
    void oneInjectedFactorAmongSeveralStopsTheAppStarting() {
        new ApplicationContextRunner().withUserConfiguration(TwoFactorsOneConsumer.class)
                .run(context -> assertThat(context).hasFailed().getFailure().rootCause().isInstanceOf(NoUniqueBeanDefinitionException.class));
    }

    @Test
    void theQuickFixWithPrimaryStartsAndQuotesWithOneFactorOnly() {
        new ApplicationContextRunner().withUserConfiguration(SomeoneAddedPrimary.class).run(context -> {
            assertThat(context).hasNotFailed();
            assertThat(context.getBean(OldQuoteService.class).quote(SENIOR_IN_EUROPE)).isZero();   // age x nothing: a free policy
        });
    }

    @Test
    void theOrderOfTheFactorsChangesThePrice() {
        List<PremiumFactor> right = List.of(new Factors.Base(), new Factors.DestinationRisk(), new Factors.Age(), new Factors.AdventureSports(), new Factors.Minimum());
        List<PremiumFactor> scanned = List.of(new Factors.Base(), new Factors.DestinationRisk(), new Factors.AdventureSports(), new Factors.Age(), new Factors.Minimum());
        assertThat(applyInOrder(right, SENIOR_IN_EUROPE)).isEqualTo(183_875);
        assertThat(applyInOrder(scanned, SENIOR_IN_EUROPE)).isEqualTo(223_875);   // the adventure loading multiplied by age: Rs 400 more
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

## At startup

The app's own log line from the run that captured the examples (`docs/captures/startup-log.txt`): the factors, in the order every quote will use.

``` console
Premium factors, in order: [Base, DestinationRisk, Age, AdventureSports, Minimum]
```

## Try it yourself

``` code
curl -X POST http://localhost:8080/premium-quotes -H "Content-Type: application/json" \
     -d '{"age":67,"destination":"EUROPE","days":10,"adventureSports":true}'
```

## Troubleshooting

| You see                                        | Cause                                                     | Fix                                                   |
|------------------------------------------------|-----------------------------------------------------------|-------------------------------------------------------|
| `NoUniqueBeanDefinitionException` at startup   | Something asks for one `PremiumFactor` or one `Rounding`. | Ask for a `List`, or add `@Qualifier`.                |
| `Premium factor … shares @Order(…)` at startup | Two factors have the same position.                       | Give each a different `@Order`.                       |
| `400` for a missing `adventureSports`          | A primitive `boolean` in the request record.              | Use `Boolean`: Jackson 3 refuses a missing primitive. |

## Project layout

``` tree
stations/029-travel-insurance-premium-factors/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/bimaly/premiums/
│   ├── PremiumQuoteController.java   ├── PremiumCalculator.java
│   ├── PremiumFactor.java            ├── Factors.java   ├── Rounding.java
│   ├── Trip.java                     └── PremiumsApplication.java
├── src/test/java/com/bimaly/premiums/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/bimaly/premiums/PremiumQuoteController.java`

Does  
Validates the request and asks the calculator for a quote.

Why  
The age limit is a product rule for this channel, so it lives here, not in a factor.

Without it  
Pricing logic in the controller.

#### `src/main/java/com/bimaly/premiums/PremiumCalculator.java`

Does  
Runs every factor in order, then rounds.

Why  
`List<PremiumFactor>` from Spring, sorted by `@Order`; a new factor does not change this class.

Without it  
The trap: one injected factor, or an order nobody chose.

- `@Qualifier("premium")` picks the rounding that charges; the unqualified one is the `@Primary`.
- `@PostConstruct` checks the orders once, after injection, before any quote.

#### `src/main/java/com/bimaly/premiums/Factors.java`

Does  
The five factors, each a bean with its `@Order`.

Why  
Small, stateless, independently testable steps.

Without it  
One class that knows every rate.

#### `src/main/java/com/bimaly/premiums/PremiumFactor.java`

The interface every factor implements, and the breakdown step it returns.

#### `src/main/java/com/bimaly/premiums/Rounding.java`

Two beans of one type: nearest rupee (`@Primary`) and up to the rupee (`@Qualifier("premium")`).

#### `src/main/java/com/bimaly/premiums/Trip.java`

What a quote is for.

#### `src/main/resources/application.yaml`

Problem bodies for every error.

#### `src/main/java/com/bimaly/premiums/PremiumsApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                     | Test class                     | Result |
|---------------|-----------------------------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (no cover for the age) | `PremiumQuoteContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                            | `FactorOrderTrapTest` (3)      | pass   |
| This station  | Order, qualifier and primary, scopes, the startup check         | `FactorWiringTest` (4)         | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.bimaly.premiums.FactorOrderTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.bimaly.premiums.PremiumQuoteContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.bimaly.premiums.FactorWiringTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/bimaly/premiums/FactorOrderTrapTest.java`

Written first: small contexts built with `ApplicationContextRunner` that fail to start, or start wrong, and the same factors in two orders.

#### `src/test/java/com/bimaly/premiums/PremiumQuoteContractTest.java`

Quotes and their breakdowns, looked up by factor name so a new factor does not break them.

#### `src/test/java/com/bimaly/premiums/FactorWiringTest.java`

The real context's list order, the two rounding beans, singletons without state, and the duplicate-order check.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/bimaly/premiums/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=NewFactorChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 14 tests pass (12 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## A new factor, nothing else

A pre-existing medical condition adds 40% to the cover cost, after age and before the adventure add-on. Add it without editing `PremiumCalculator`.

**Done when:** the test in `NewFactorChallengeTest` passes, and the station's tests still pass.

Hints

- A new `@Component` implementing `PremiumFactor`, with an `@Order` between 30 and 40.
- The request and the trip need the new field; keep the old trip constructor for code that does not know it.

#### `challenge/NewFactorChallengeTest.java`

``` code
package com.bimaly.premiums;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: a pre-existing medical condition adds 40% to the cover cost (after age, before the adventure add-on).
 * Add the factor without editing PremiumCalculator: a new bean with the right @Order is enough.
 */
@SpringBootTest
@AutoConfigureMockMvc
class NewFactorChallengeTest {

    @Autowired
    MockMvc mvc;

    @Test
    void aPreExistingConditionIsLoadedBeforeTheAdventureAddOn() throws Exception {
        mvc.perform(post("/premium-quotes").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"age\":67,\"destination\":\"EUROPE\",\"days\":10,\"adventureSports\":true,\"preExistingCondition\":true}"))
                .andExpect(jsonPath("$.breakdown[3].factor").value("pre-existing condition"))
                .andExpect(jsonPath("$.breakdown[3].totalPaise").value(187_425))   // 133,875 x 1.40
                .andExpect(jsonPath("$.premiumPaise").value(237_500));             // + 50,000 adventure, rounded up
        mvc.perform(post("/premium-quotes").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"age\":67,\"destination\":\"EUROPE\",\"days\":10,\"adventureSports\":true}"))
                .andExpect(jsonPath("$.premiumPaise").value(183_900));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 25 minutes

## A campaign you can switch off

A Diwali campaign takes 10% off before the minimum. The factor exists only while `bimaly.campaign.diwali=true`; switching it off is a configuration change, not a release.

**Done when:** the test in `CampaignDiscountChallengeTest` passes.

Hints

- `@ConditionalOnProperty("bimaly.campaign.diwali")` on the factor: no property, no bean.
- An `@Order` below the minimum's 100.

#### `challenge/CampaignDiscountChallengeTest.java`

``` code
package com.bimaly.premiums;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: a Diwali campaign takes 10% off, before the minimum is applied. The factor exists only when
 * bimaly.campaign.diwali=true (@ConditionalOnProperty), so switching the campaign off is a configuration change.
 */
class CampaignDiscountChallengeTest {

    final ApplicationContextRunner app = new ApplicationContextRunner()
            .withUserConfiguration(Rounding.Beans.class, Factors.Base.class, Factors.DestinationRisk.class, Factors.Age.class,
                    Factors.AdventureSports.class, Factors.Minimum.class, CampaignDiscount.class, PremiumCalculator.class);

    static final Trip SENIOR_IN_EUROPE = new Trip(67, Trip.Destination.EUROPE, 10, true);

    @Test
    void theDiscountAppliesOnlyWhenTheCampaignIsOn() {
        app.withPropertyValues("bimaly.campaign.diwali=true").run(ctx -> {
            PremiumCalculator.Quote q = ctx.getBean(PremiumCalculator.class).quote(SENIOR_IN_EUROPE);
            assertThat(q.breakdown()).extracting(PremiumFactor.Step::factor).contains("campaign");
            assertThat(q.premiumPaise()).isEqualTo(165_500);   // 183,875 less 10% = 165,487.5 -> 165,488, rounded up
        });
        app.run(ctx -> assertThat(ctx.getBean(PremiumCalculator.class).quote(SENIOR_IN_EUROPE).breakdown())
                .extracting(PremiumFactor.Step::factor).isEqualTo(List.of("base", "destination", "age", "adventure", "minimum")));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Factors as configuration

The actuaries want to change multipliers weekly without a release. Which parts would you move to configuration (the numbers, the bands, the order?) and which stay in code? How would you stop a bad configuration from reaching customers: validation at startup, a preview endpoint, or a second approver?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: one-of-several, the `@Primary` quick fix, and two orders.
2.  Split the premium into factor beans with explicit `@Order`.
3.  Inject them as a list; check the orders at startup.
4.  Add the two rounding beans and pick each with `@Qualifier` or `@Primary`.

## Design alternatives and trade-offs

| Approach                        | What it costs                                             | Verdict                   |
|---------------------------------|-----------------------------------------------------------|---------------------------|
| Factor beans in an ordered list | One class per factor.                                     | Chosen                    |
| One premium class               | Every change touches every price.                         | The starting point        |
| `@Primary` to silence the error | Starts, with only one factor.                             | The trap                  |
| List without `@Order`           | Order depends on scanning: unspecified.                   | The trap                  |
| Factors as configuration rows   | A rules format and its validation; no release per change. | When changes are frequent |

## Database design

None in this station. If rates move to a database: a `premium_rates` table with effective dates (like station 016), and the quote records the rates it used, so a past quote can always be explained.

# 3 · Go deeper: Production

Fail fast  
A wrong factor order is a wrong price for every customer. The startup check turns it into a deployment that never starts, which is far cheaper.

Scopes  
Factors are singletons shared by all requests at once, so they hold no per-quote state. Anything per quote lives in local variables or the returned breakdown.

Explainability  
The breakdown shows every step. Customers and regulators ask "why this price?"; the answer is in the response.

Money  
Paise throughout, rounded per step and once more at the end, up, as the insurer's rule says.

# 3 · Go deeper: Interview

## Interview takeaways

What happens when you inject one bean and several exist?

Spring fails with NoUniqueBeanDefinitionException. Fix it by injecting a List of all of them, or choosing one with @Qualifier; @Primary only sets a default.

In what order does Spring inject a List of beans?

Sorted by @Order or the Ordered interface when present. Without them the order is not specified, so never rely on it.

@Qualifier or @Primary?

@Primary marks the default for anyone who does not ask for a specific one. @Qualifier asks for a specific one. Use both: a sensible default, and explicit choices where it matters.

What is the default bean scope, and what follows?

Singleton: one instance shared by every request. So beans must not keep per-request state in fields.

What is @PostConstruct for?

Code that runs once after injection, before the bean is used: a good place to validate configuration and fail at startup.

## Self-check rubric

| Area        | Meets the bar                | Above the bar                                    |
|-------------|------------------------------|--------------------------------------------------|
| Correctness | All 12 tests pass.           | You can compute case 1's premium by hand.        |
| Wiring      | A list in an explicit order. | Why @Primary was the wrong fix.                  |
| Lifecycle   | The startup check.           | Other things worth checking at startup.          |
| Explanation | Why order changes the price. | Factors in code versus factors in configuration. |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist when several beans share a type:

- Does anything inject one where several exist, saved by a `@Primary`?
- Does the order of a list matter, and is it written down with `@Order`?
- Does any singleton keep per-request state in a field?
- What happens at startup if the wiring is wrong?
