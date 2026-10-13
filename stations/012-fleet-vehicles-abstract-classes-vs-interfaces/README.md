# Station 012 · Fleet vehicles: abstract classes vs interfaces

Foundations · 0–1 years · Core · Logistics · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · interfaces, enums, records · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Five vehicles are fixed in the code. Service intervals are demo rules, not any manufacturer's schedule.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 8 tests.

# 1 · Understand

## The problem in real life

1.  **Dakroute's fleet app grew one class at a time**

    Vehicle, then FuelVehicle, then Truck, Van and Bike underneath, with shared code copied between them.

2.  **An EV van arrived**

    It was made a subclass of Van, so it inherited an engine oil change. Fixing that took changes in nine places, and someone's "diesel filter for trucks" in the shared parent showed up on petrol bikes.

3.  **The fix**

    Describe a vehicle by its parts: a powertrain (diesel, petrol, electric) and a body (truck, van, two-wheeler). Each part lists its own tasks; a vehicle's plan is its parts' tasks together.

"Is a" is a strong promise: a child gets everything the parent has, today and after every future change. "Has a" lets you pick exactly the parts you need.

## What are we building?

`GET /fleet/vehicles/{id}/service-plan`: the maintenance tasks for one vehicle, each with the kilometre reading when it is next due, soonest first. An EV van gets battery checks and van checks, and never an oil change.

## An everyday analogy

A tiffin service. One way is to have a "North Indian Thali", a "North Indian Thali Without Onion", a "Jain North Indian Thali Without Onion", each a copy of the one above with changes. The other way is to let each customer choose a base, a dal and a sabzi. The second way never serves onions to a Jain customer by accident when the base thali changes.

## How it works in 4 steps

1.  **A vehicle is two parts**: a powertrain and a body.
2.  **Each part lists its tasks**, such as "Engine oil change every 15,000 km" for diesel or "Brake check every 15,000 km" for a van.
3.  **The planner asks each part** for its tasks without knowing which part it is (polymorphism).
4.  **For each task**, the next due reading is the next multiple of its interval; the list is sorted soonest first.

Check yourself: Dakroute buys a CNG van. With composition, what has to change?

Only a new powertrain value, CNG, with its own tasks, and the van itself in the fleet list. The body VAN, the planner and every other vehicle stay untouched. Practice challenge 1 does exactly this.

## What this station is not

- **No service history.** "Next due" is the next multiple of the interval, not based on when the work was last done.
- **Not real schedules.** Intervals are demo rules; real ones come from each manufacturer's manual.
- **No database.** Five vehicles are fixed in code.

## Key terms

| Term                   | Simple meaning                                                                        | Everyday example                                              | In this project                                         |
|------------------------|---------------------------------------------------------------------------------------|---------------------------------------------------------------|---------------------------------------------------------|
| **Inheritance**        | A class takes everything from a parent class (`extends`).                             | A child inheriting the family house, leaks and all.           | The trap's `OldEvVan extends OldVan`.                   |
| **Abstract class**     | A parent class that cannot be created on its own and can hold shared code and fields. | A recipe base: "every curry starts with onions".              | The trap's `OldVehicle`.                                |
| **Interface**          | A promise of what a class can do, with no stored data.                                | A plug socket shape: anything that fits can be plugged in.    | `ServiceItems`: "I can list service tasks".             |
| **Composition**        | Building something out of parts it has, instead of a parent it is.                    | A thali: you choose the dishes, nothing comes with the plate. | A vehicle has a powertrain and a body.                  |
| **Polymorphism**       | Calling the same method on different kinds of objects, each answering its own way.    | Asking every guest "what will you eat?"                       | `part.tasks()` on a powertrain or a body.               |
| **Fragile base class** | A change in a parent class breaks children that never asked for it.                   | Changing the house's wiring, and every flat's lights flicker. | A diesel filter task added for trucks appears on bikes. |

# 2 · Build: Spec

## Business problem

**Dakroute** (a fictional logistics company) runs trucks, vans and two-wheelers. Its fleet app models them as a tree of classes. When the first EV van arrived, it was added as a subclass of Van and inherited an engine oil change, so the workshop booked oil changes for an electric van. Removing it touched nine classes. A month later a "diesel particulate filter" task, added to the shared fuel-vehicle parent for trucks, appeared on every petrol bike.

## Acceptance criteria

1.  **Given** a diesel truck at 128,400 km, **then** its plan has the diesel tasks and the truck tasks, soonest first; the 15,000 km oil change is next due at 135,000 km (in 6,600 km).
2.  **Given** an electric van, **then** its plan has battery and van tasks and no engine oil change.
3.  **Given** a petrol two-wheeler, **then** no diesel tasks, and the petrol oil interval (10,000 km).
4.  **Given** a task within 10% of its interval, **then** it is marked `dueSoon`.
5.  **Given** an unknown vehicle, **then** `404`; a non-numeric id, `400`.

## Requirements

- A vehicle is a powertrain plus a body. Each contributes its own tasks; nothing is inherited.
- Next due = the next multiple of the interval at or above the odometer (at least one interval).
- Tasks are sorted by km until due, then by name.
- Errors are RFC 9457 problems.

## Learning objectives

- Explain the difference between an abstract class and an interface, and when each fits.
- Prefer composition to inheritance, and say why.
- Use polymorphism through an interface implemented by enums.
- Recognise the fragile base class problem in code you review.

# 2 · Build: API contract

## Endpoint

| Method | Path                                | Purpose                                           |
|--------|-------------------------------------|---------------------------------------------------|
| `GET`  | `/fleet/vehicles/{id}/service-plan` | The vehicle's parts and its tasks, soonest first. |

## Each task

| Field                  | Meaning                                                             |
|------------------------|---------------------------------------------------------------------|
| `task`, `everyKm`      | What to do, and how often.                                          |
| `nextDueKm`, `dueInKm` | The odometer reading when it is next due, and how far away that is. |
| `dueSoon`              | Within 10% of the interval (a demo rule).                           |

## Status codes

| Status | When                   |
|--------|------------------------|
| 200    | The vehicle exists     |
| 400    | The id is not a number |
| 404    | No such vehicle        |

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the diesel truck

**Why:** DIESEL tasks plus TRUCK tasks, soonest first. Two tasks due in 1,600 km are ordered by name.

Request

``` code
GET /fleet/vehicles/1/service-plan HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 703

{
  "vehicleId": 1,
  "registration": "KA01TR1234",
  "model": "Tata Prima 2830.K",
  "powertrain": "DIESEL",
  "body": "TRUCK",
  "odometerKm": 128400,
  "tasks": [
    {
      "task": "Axle greasing",
      "everyKm": 5000,
      "nextDueKm": 130000,
      "dueInKm": 1600,
      "dueSoon": false
    },
    {
      "task": "Brake check",
      "everyKm": 10000,
      "nextDueKm": 130000,
      "dueInKm": 1600,
      "dueSoon": false
    },
    {
      "task": "Engine oil change",
      "everyKm": 15000,
      "nextDueKm": 135000,
      "dueInKm": 6600,
      "dueSoon": false
    },
    {
      "task": "Tyre rotation",
      "everyKm": 15000,
      "nextDueKm": 135000,
      "dueInKm": 6600,
      "dueSoon": false
    },
    {
      "task": "Fuel filter",
      "everyKm": 30000,
      "nextDueKm": 150000,
      "dueInKm": 21600,
      "dueSoon": false
    },
    {
      "task": "Diesel particulate filter clean",
      "everyKm": 60000,
      "nextDueKm": 180000,
      "dueInKm": 51600,
      "dueSoon": false
    }
  ]
}
```

### Case 2: the EV van

**Why:** ELECTRIC plus VAN: battery checks and van checks, no oil change. The battery check is `dueSoon` (1,050 km of a 20,000 km interval).

Request

``` code
GET /fleet/vehicles/3/service-plan HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 499

{
  "vehicleId": 3,
  "registration": "KA01EV9012",
  "model": "Tata Ace EV",
  "powertrain": "ELECTRIC",
  "body": "VAN",
  "odometerKm": 18950,
  "tasks": [
    {
      "task": "Battery health check",
      "everyKm": 20000,
      "nextDueKm": 20000,
      "dueInKm": 1050,
      "dueSoon": true
    },
    {
      "task": "Tyre rotation",
      "everyKm": 10000,
      "nextDueKm": 20000,
      "dueInKm": 1050,
      "dueSoon": false
    },
    {
      "task": "Brake check",
      "everyKm": 15000,
      "nextDueKm": 30000,
      "dueInKm": 11050,
      "dueSoon": false
    },
    {
      "task": "Battery coolant",
      "everyKm": 40000,
      "nextDueKm": 40000,
      "dueInKm": 21050,
      "dueSoon": false
    }
  ]
}
```

### Case 3: the petrol two-wheeler

**Why:** PETROL plus TWO_WHEELER: a 10,000 km oil change, chain lubrication, no diesel filter.

Request

``` code
GET /fleet/vehicles/4/service-plan HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 497

{
  "vehicleId": 4,
  "registration": "KA01BK3456",
  "model": "Hero Splendor+",
  "powertrain": "PETROL",
  "body": "TWO_WHEELER",
  "odometerKm": 9600,
  "tasks": [
    {
      "task": "Brake check",
      "everyKm": 5000,
      "nextDueKm": 10000,
      "dueInKm": 400,
      "dueSoon": true
    },
    {
      "task": "Chain lubrication",
      "everyKm": 1000,
      "nextDueKm": 10000,
      "dueInKm": 400,
      "dueSoon": false
    },
    {
      "task": "Engine oil change",
      "everyKm": 10000,
      "nextDueKm": 10000,
      "dueInKm": 400,
      "dueSoon": true
    },
    {
      "task": "Spark plugs",
      "everyKm": 20000,
      "nextDueKm": 20000,
      "dueInKm": 10400,
      "dueSoon": false
    }
  ]
}
```

### Case 4: unknown vehicle

**Why:** `404` problem.

Request

``` code
GET /fleet/vehicles/99/service-plan HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No vehicle has this id.",
  "instance": "/fleet/vehicles/99/service-plan",
  "status": 404,
  "title": "Vehicle not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                       | What happens                                        | Proved by                                                                                   |
|--------------------------------------------|-----------------------------------------------------|---------------------------------------------------------------------------------------------|
| Diesel truck                               | Diesel and truck tasks, soonest first, ties by name | `aDieselTruckGetsEngineAndTruckTasksSoonestFirst`                                           |
| Electric van                               | Battery and van tasks; dueSoon at 10%               | `anElectricVanGetsBatteryAndVanTasks`                                                       |
| Petrol two-wheeler                         | Petrol interval; no diesel tasks                    | `aPetrolBikeGetsEngineAndTwoWheelerTasks`, `composedVehiclesGetOnlyTheTasksOfTheirOwnParts` |
| Every one of the 9 combinations            | Exactly its two parts' tasks                        | `everyCombinationOfPartsGetsExactlyTheTasksOfItsTwoParts`                                   |
| Odometer 0, 14,999, exactly 30,000, 30,001 | Due at 15,000; 15,000; now; 45,000                  | `nextDueIsTheNextMultipleOfTheInterval`                                                     |
| Unknown vehicle; id "truck"                | `404`; `400`                                        | `anUnknownVehicleIs404AndANonNumberIs400`                                                   |

## The trap

Plausible but wrong

Deep inheritance trees where one change in the base class breaks every vehicle.

The "before" code is a tree of abstract classes: `OldVehicle` → `OldFuelVehicle` → `OldVan` → `OldEvVan`. Each step looks reasonable. The first test shows the result: the EV van inherits an oil change, and a task added to the fuel parent "for the trucks" lands on a petrol bike. The second test asks the real API, built from parts, and neither happens. Removing the body from `Vehicle.parts()` was tried while building: 4 tests went red.

``` code
package com.dakroute.fleet;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: it reproduces the problem before the fix.
 * The "before" code is a family tree of abstract classes, the way the fleet app grew.
 */
class DeepInheritanceTrapTest extends ApiTest {

    abstract static class OldVehicle {
        List<String> tasks() {
            return new ArrayList<>(List.of("Brake check"));
        }
    }

    abstract static class OldFuelVehicle extends OldVehicle {
        @Override
        List<String> tasks() {
            List<String> t = super.tasks();
            t.add("Engine oil change");
            t.add("Diesel particulate filter clean"); // added later "for the trucks", in the shared parent
            return t;
        }
    }

    static class OldVan extends OldFuelVehicle {
        @Override
        List<String> tasks() {
            List<String> t = super.tasks();
            t.add("Tyre rotation");
            return t;
        }
    }

    /** "An EV van is a van", so it extends OldVan, and inherits everything a fuel van needs. */
    static class OldEvVan extends OldVan {
        @Override
        List<String> tasks() {
            List<String> t = super.tasks();
            t.add("Battery health check");
            return t;
        }
    }

    static class OldPetrolBike extends OldFuelVehicle {
    }

    @Test
    void theEvVanInheritsAnOilChangeAndThePetrolBikeADieselFilter() {
        assertThat(new OldEvVan().tasks()).contains("Engine oil change");                 // an EV has no engine oil
        assertThat(new OldPetrolBike().tasks()).contains("Diesel particulate filter clean"); // nor does a petrol bike
    }

    @Test
    void composedVehiclesGetOnlyTheTasksOfTheirOwnParts() throws Exception {
        mvc.perform(get("/fleet/vehicles/3/service-plan"))   // Tata Ace EV: ELECTRIC + VAN
                .andExpect(jsonPath("$.tasks[*].task", hasItem("Battery health check")))
                .andExpect(jsonPath("$.tasks[*].task", not(hasItem("Engine oil change"))));
        mvc.perform(get("/fleet/vehicles/4/service-plan"))   // Hero Splendor+: PETROL + TWO_WHEELER
                .andExpect(jsonPath("$.tasks[*].task", not(hasItem("Diesel particulate filter clean"))));
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
./mvnw test                 # all 8 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

``` code
curl http://localhost:8080/fleet/vehicles/3/service-plan
curl http://localhost:8080/fleet/vehicles/5/service-plan
```

Vehicle 5 is an electric two-wheeler: a combination nobody wrote a class for. Compare its tasks with vehicle 3's.

## Troubleshooting

| You see                            | Cause                        | Fix                                                      |
|------------------------------------|------------------------------|----------------------------------------------------------|
| `404`                              | Only vehicles 1 to 5 exist.  | Use one of those ids.                                    |
| `release version 25 not supported` | Maven is using an older JDK. | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/012-fleet-vehicles-abstract-classes-vs-interfaces/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/dakroute/fleet/
│   ├── ServicePlanController.java   ├── ServicePlanner.java   ├── Fleet.java
│   ├── Vehicle.java                 ├── ServiceItems.java     ├── ServiceTask.java
│   ├── Powertrain.java              ├── Body.java             └── FleetApplication.java
├── src/test/java/com/dakroute/fleet/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/dakroute/fleet/ServicePlanController.java`

Does  
Finds the vehicle and returns its plan.

Why  
HTTP in one place.

Without it  
No API.

#### `src/main/java/com/dakroute/fleet/Vehicle.java`

Does  
A record that *has* a powertrain and a body.

Why  
Composition: any powertrain goes with any body, with no new class.

Without it  
A class per combination (EvVan, DieselVan, PetrolVan…), each inheriting from something.

#### `src/main/java/com/dakroute/fleet/ServiceItems.java`

Does  
The interface: "I can list service tasks".

Why  
It is all the planner needs to know about a part.

Without it  
The planner would need an `if` for every kind of part.

#### `src/main/java/com/dakroute/fleet/Powertrain.java`

Does  
An enum that implements `ServiceItems`: each value carries its tasks.

Why  
Adding CNG is one new value.

Without it  
Tasks spread over subclasses.

#### `src/main/java/com/dakroute/fleet/Body.java`

Does  
The same idea for bodies.

Why  
Independent of the powertrain.

Without it  
Truck tasks mixed into engine classes.

#### `src/main/java/com/dakroute/fleet/ServicePlanner.java`

Does  
Asks every part for its tasks, works out when each is next due, sorts soonest first.

Why  
One place for the arithmetic, tested without Spring.

Without it  
Each vehicle class computing its own dates differently.

- `Math.ceilDiv(odometer, every) * every` is the next multiple, at least one interval.

#### `src/main/java/com/dakroute/fleet/Fleet.java`

The five vehicles.

#### `src/main/java/com/dakroute/fleet/ServiceTask.java`

A task and its interval.

#### `src/main/resources/application.yaml`

Turns on Spring Boot's RFC 9457 problem bodies for every error.

#### `src/main/java/com/dakroute/fleet/FleetApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                    | Result |
|---------------|------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `ServicePlanContractTest` (4) | pass   |
| Every station | Reproduce the failure before the fix     | `DeepInheritanceTrapTest` (2) | pass   |
| This station  | Arithmetic and all 9 combinations        | `ServicePlannerTest` (2)      | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.fleet.DeepInheritanceTrapTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.fleet.ServicePlannerTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.dakroute.fleet.ServicePlanContractTest
[INFO] Tests run: 8, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/dakroute/fleet/DeepInheritanceTrapTest.java`

Written first: the class tree hands an EV van an oil change and a petrol bike a diesel filter.

#### `src/test/java/com/dakroute/fleet/ServicePlanContractTest.java`

Three different vehicles, exact plans, and the refusals.

#### `src/test/java/com/dakroute/fleet/ServicePlannerTest.java`

Due-date arithmetic, and every powertrain with every body.

#### `src/test/java/com/dakroute/fleet/ApiTest.java`

Shared setup: the whole app through MockMvc.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/dakroute/fleet/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=CngPowertrainChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 8 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 13 tests pass (8 station tests and 5 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## A CNG van joins the fleet

Add a CNG powertrain (oil change every 10,000 km, gas leak check every 10,000 km, cylinder hydro-test every 1,00,000 km) and vehicle 6, a Bajaj Maxima Cargo CNG van, KA01CN2468, at 51,000 km. Count how many files you change.

**Done when:** both tests in `CngPowertrainChallengeTest` pass: the CNG van's plan is right and vehicle 2's is unchanged.

Hints

- Two files: a new enum value and a new fleet entry. With the old class tree it would have been a new class and a fight with its parents.
- The station's combination test now covers CNG with every body too, for free.

#### `challenge/CngPowertrainChallengeTest.java`

``` code
package com.dakroute.fleet;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasItems;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: Dakroute buys a CNG cargo van (vehicle 6, KA01CN2468, Bajaj Maxima Cargo CNG, 51,000 km).
 * A CNG engine needs an oil change every 10,000 km, a gas leak check every 10,000 km and a cylinder hydro-test
 * every 1,00,000 km. Add it, and prove no other vehicle's plan changed.
 */
class CngPowertrainChallengeTest extends ApiTest {

    @Test
    void theCngVanGetsCngAndVanTasks() throws Exception {
        mvc.perform(get("/fleet/vehicles/6/service-plan"))
                .andExpect(jsonPath("$.powertrain").value("CNG"))
                .andExpect(jsonPath("$.body").value("VAN"))
                .andExpect(jsonPath("$.tasks[*].task", hasItems("Gas leak check", "Cylinder hydro-test", "Engine oil change", "Brake check")));
    }

    @Test
    void theOtherVehiclesAreUntouched() throws Exception {
        mvc.perform(get("/fleet/vehicles/2/service-plan"))
                .andExpect(jsonPath("$.tasks[*].task", contains("Brake check", "Engine oil change", "Tyre rotation", "Spark plugs")));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Beginner-friendly · about 20 minutes

## Only what is due soon

The workshop asks what is due in the next N km. Add an optional `withinKm` parameter (1 to 1,00,000; the boundary is included).

**Done when:** all three tests in `WithinKmChallengeTest` pass.

Hints

- Filter the planned list; do not touch the planner's arithmetic.
- `@Min`/`@Max` on a parameter need the validation starter: `challenge/solution/pom-additions.xml` has the dependency.

#### `challenge/WithinKmChallengeTest.java`

``` code
package com.dakroute.fleet;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: the workshop asks "what is due in the next N km?": an optional withinKm filter, 1 to 1,00,000. */
class WithinKmChallengeTest extends ApiTest {

    @Test
    void onlyTasksDueWithinTheDistanceAreListed() throws Exception {
        mvc.perform(get("/fleet/vehicles/1/service-plan").param("withinKm", "2000"))
                .andExpect(jsonPath("$.tasks[*].task", contains("Axle greasing", "Brake check")));
    }

    @Test
    void theBoundaryIsIncluded() throws Exception {
        mvc.perform(get("/fleet/vehicles/1/service-plan").param("withinKm", "6600"))
                .andExpect(jsonPath("$.tasks[*].task", contains("Axle greasing", "Brake check", "Engine oil change", "Tyre rotation")));
    }

    @Test
    void outOfRangeIs400() throws Exception {
        mvc.perform(get("/fleet/vehicles/1/service-plan").param("withinKm", "0")).andExpect(status().isBadRequest());
        mvc.perform(get("/fleet/vehicles/1/service-plan").param("withinKm", "100001")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When is an abstract class the right tool?

Dakroute's telematics team wants every vehicle tracker to share the same connection, retry and logging code, with each tracker brand filling in how it reads GPS. Sketch it once with an abstract class (a template method) and once with an interface plus a helper class. Which would you choose, and what would make you change your mind?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the class tree gives the EV van an oil change.
2.  Name the independent parts of a vehicle: powertrain and body.
3.  Write one small interface for what the planner needs, and let both enums implement it.
4.  Compose a vehicle from the two parts; plan by asking each part.
5.  Test every combination, so no part can leak into another.

## Abstract class or interface?

|                      | Abstract class                                              | Interface                                       |
|----------------------|-------------------------------------------------------------|-------------------------------------------------|
| Holds fields (state) | Yes                                                         | No (constants only)                             |
| Shares method code   | Yes                                                         | Only `default` methods, without state           |
| A class can have     | One parent                                                  | Many interfaces                                 |
| Says                 | "is a kind of"                                              | "can do"                                        |
| Good for             | Close relatives sharing state and a fixed sequence of steps | Any type that can play a role, unrelated or not |

## Design alternatives and trade-offs

| Approach                                             | What it costs                                                             | Verdict      |
|------------------------------------------------------|---------------------------------------------------------------------------|--------------|
| Interface + enums + composition                      | A part per independent idea; combinations are free.                       | Chosen       |
| Deep tree of abstract classes                        | Children inherit everything, including later mistakes (the trap).         | Wrong here   |
| One class with `if (type == ...)`                    | Every new type edits the same method; station 014 shows where that leads. | Wrong        |
| Abstract class for shared plumbing (template method) | Right when subclasses truly share state and steps, as in Challenge 3.     | When it fits |

## Database design

None in this station. In a database, powertrain and body are two columns (or two small tables) and tasks hang off each; a vehicle row points at one of each.

# 3 · Go deeper: Production

Maintainability  
A new powertrain or body is one enum value. A new kind of rule for every vehicle is one more part in `Vehicle.parts()`.

Correctness  
The combination test guards the core promise: a vehicle gets exactly its parts' tasks.

Data  
Real intervals vary by model and duty; in production they come from data, not code. The structure stays the same.

# 3 · Go deeper: Interview

## Interview takeaways

Abstract class or interface: how do you choose?

Interface when you describe a role many unrelated types can play; it holds no state and a class can implement many. Abstract class when close relatives share state and a fixed series of steps. When in doubt, start with an interface.

What does 'favour composition over inheritance' mean?

Build objects from parts they have, rather than parents they are. Parts can be combined freely and changed independently; a parent's change reaches every child.

What is the fragile base class problem?

A change to a parent class silently changes every subclass, including ones the change was never meant for, like a truck task appearing on bikes.

What is polymorphism here?

The planner calls tasks() on each part without knowing if it is a powertrain or a body; each answers in its own way.

Can an enum implement an interface?

Yes. Each enum value is an object; it can carry data and implement methods, which makes small fixed sets of behaviour very simple.

## Self-check rubric

| Area        | Meets the bar                                | Above the bar                                                   |
|-------------|----------------------------------------------|-----------------------------------------------------------------|
| Correctness | All 8 tests pass.                            | You can say which tests fail if a part is left out.             |
| Design      | A vehicle is composed of parts.              | You can name a case where an abstract class is the better tool. |
| Tests       | Every combination is tested.                 | You can explain why that one test replaces nine.                |
| Explanation | The table: abstract class against interface. | You can spot a fragile base class in someone else's code.       |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any class hierarchy:

- Is every subclass truly "a kind of" its parent, for every method it inherits?
- How many levels deep is the tree? Could the levels be parts instead?
- If you changed the parent, which children would change without asking?
- Is there copied code that a shared part could replace?
