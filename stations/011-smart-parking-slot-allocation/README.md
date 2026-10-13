# Station 011 · Smart parking slot allocation

Foundations · 0–1 years · Core · Smart cities · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · enums · TreeSet · java.time.Clock · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** One 6-floor building with 360 slots exists only in the app's memory. No gate hardware, cameras or payments: a fee is a number on the receipt.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 15 tests.

# 1 · Understand

## The problem in real life

1.  **Neha drives into an empty mall parking at 9 a.m.**

    The entry gate sends her to floor 5, at the far end. Ground-floor slots next to the exit stay empty all morning.

2.  **A biker gets a car slot**

    The gate gave the first free slot on its list, whatever its size, so bikes took car slots and cars were turned away while bike slots stood free.

3.  **The fix**

    Keep the free slots of each type in order, nearest first. Each entry takes the top one; each exit puts its slot back in its place.

If you will ask "which is the best one?" thousands of times, keep things sorted once, instead of searching every time.

## What are we building?

Two endpoints: an entry gate (`POST /parking/entries`) that hands out a ticket for the nearest free slot of the right size, and an exit gate (`POST /parking/exits/{ticketId}`) that frees the slot and prints a receipt, charging every started hour.

## An everyday analogy

A hospital keeps a waiting list sorted by urgency. When a doctor is free, the nurse calls the top name; nobody re-reads the whole register each time. When a patient leaves and comes back, they go back into the list at their place. Free parking slots, sorted by distance, work the same way.

## How it works in 4 steps

1.  **At start-up**, every slot goes into one of two sorted sets, cars or bikes, nearest first.
2.  **A vehicle enters**: the gate takes the first slot from the set for its type. Nothing left: `409`.
3.  **The ticket** records the slot and the entry time.
4.  **At exit**, the fee counts every started hour; the slot goes back into its set, in its place.

Check yourself: a car on the ground floor leaves. The next car arrives. Where does it go?

To that ground-floor slot, if it is now the nearest free car slot. Putting the slot back into the sorted set places it at the front again, so the next `pollFirst` returns it.

## What this station is not

- **No hardware.** No boom barriers, cameras or number-plate readers.
- **No payment.** The fee is a number on the receipt. Rates are demo rules, not any city's tariff.
- **One building, in memory.** A restart forgets every ticket.

## Key terms

| Term            | Simple meaning                                                            | Everyday example                                           | In this project                                  |
|-----------------|---------------------------------------------------------------------------|------------------------------------------------------------|--------------------------------------------------|
| **Model**       | Classes that mirror the real things: slot, vehicle type, ticket, receipt. | A toy model of a building.                                 | `Slot`, `Ticket`, `Garage`                       |
| **Enum**        | A fixed list of named values, which can also carry data.                  | The sizes on a T-shirt label.                              | `VehicleType.CAR` knows its slot type and rates. |
| **TreeSet**     | A set that keeps its items sorted all the time.                           | A queue at a counter that reorders itself by token number. | Free slots, nearest first.                       |
| **pollFirst**   | Take and remove the smallest item of a sorted set.                        | Calling the next token.                                    | The nearest free slot.                           |
| **Comparator**  | The rule for which item comes first.                                      | "Shorter walk first; if equal, lower slot number."         | `Slot.NEAREST_FIRST`                             |
| **Rounding up** | Any part of an hour counts as a whole hour.                               | A taxi meter that adds a full unit when you start one.     | 61 minutes is 2 hours.                           |
| **Clock**       | Java's source of "now" that tests can replace.                            | A stopwatch the referee controls.                          | `TestClock` in tests.                            |

# 2 · Build: Spec

## Business problem

**Parkora** (a fictional smart-parking operator) runs a 6-floor mall car park. Its gate software walks the slot sheet from the top floor and takes the first free slot of any size. Customers complain about walking from floor 5 when the ground floor is empty; bikes fill car slots; and at peak hours each entry gets slower, because every car re-reads the whole sheet.

## Acceptance criteria

1.  **Given** an empty building, **when** a car enters, **then** it gets `F0-C01`, the nearest car slot; a bike gets `F0-B01`.
2.  **Given** a freed slot that is now the nearest, **then** the next vehicle of that type gets it.
3.  **Given** no free car slots, **then** a car gets `409`, while bikes can still enter.
4.  **Given** a vehicle already inside, **when** the same plate enters again (in any spelling), **then** `409` naming its open ticket.
5.  **Given** 150 minutes parked, **then** 3 hours are charged: ₹40 + 2 × ₹30 = ₹100 for a car.
6.  **Given** the exit gate sends the same ticket twice, **then** the same receipt comes back and the slot is freed once.

## Requirements

- Slot types: bike and car. Each vehicle type uses only its own slot type.
- "Nearest" = shortest walk to the exit; ties by slot id.
- Fees (demo rules): car ₹40 first hour, ₹30 each started hour after; bike ₹20, then ₹10. Minimum one hour. Amounts in paise.
- Plates are normalised (spaces and hyphens removed, upper case with `Locale.ROOT`) and checked against a demo pattern like `MH12AB1234`.
- Entry and exit never interleave: two gates cannot hand out the same slot.

## Learning objectives

- Model a real system with records, enums and one class that owns the rules.
- Put data and behaviour on enums.
- Keep a `TreeSet` ordered with a `Comparator`, and use `pollFirst` and `add`.
- Round up correctly with `Math.ceilDiv`, and test the boundaries.
- Inject a `Clock` so time-based rules can be tested instantly.

# 2 · Build: API contract

## Endpoints

| Method | Path                        | Purpose                                                                                |
|--------|-----------------------------|----------------------------------------------------------------------------------------|
| `POST` | `/parking/entries`          | Body `{"vehicleNumber", "vehicleType": "CAR" | "BIKE"}`. `201` with a ticket and slot. |
| `POST` | `/parking/exits/{ticketId}` | `200` with the receipt; the slot is freed.                                             |

## Status codes

| Status | When                                                                        |
|--------|-----------------------------------------------------------------------------|
| 201    | Ticket issued                                                               |
| 200    | Receipt (also for a repeated exit: the same receipt)                        |
| 400    | Bad plate, unknown vehicle type, missing fields, malformed ticket id        |
| 404    | Unknown ticket                                                              |
| 409    | *No free slot* of this type, or *Already parked* (with the open `ticketId`) |

Why is exit a `POST` that may be repeated? The exit gate retries when its network drops. The first exit stores the receipt; every later call returns it unchanged, so the customer is charged once and the slot is freed once (the idempotency idea from station 008).

## Captured examples

Captured with curl from the running app on 13 Oct 2026, with the real clock, so exits happen seconds after entry. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a bike enters an empty building

**Why:** the nearest bike slot, `F0-B01`: never a car slot.

Request

``` code
POST /parking/entries HTTP/1.1
Content-Type: application/json

{
  "vehicleNumber": "KA05XY4321",
  "vehicleType": "BIKE"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 209

{
  "ticketId": "545b6169-87af-4786-a7c2-e752db08607a",
  "vehicleNumber": "KA05XY4321",
  "vehicleType": "BIKE",
  "slot": {
    "id": "F0-B01",
    "floor": 0,
    "number": 1,
    "type": "BIKE",
    "walkMetres": 3
  },
  "enteredAt": "2026-10-13T16:30:19Z"
}
```

### Case 2: a car, plate typed loosely

**Why:** `mh 12 ab-1234` is normalised to `MH12AB1234`; the nearest car slot is `F0-C01`.

Request

``` code
POST /parking/entries HTTP/1.1
Content-Type: application/json

{
  "vehicleNumber": "mh 12 ab-1234",
  "vehicleType": "CAR"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 207

{
  "ticketId": "ae866854-8cca-46ff-899c-a2008f7fff2f",
  "vehicleNumber": "MH12AB1234",
  "vehicleType": "CAR",
  "slot": {
    "id": "F0-C01",
    "floor": 0,
    "number": 1,
    "type": "CAR",
    "walkMetres": 6
  },
  "enteredAt": "2026-10-13T16:30:19Z"
}
```

### Case 3: the same car at another gate

**Why:** it is already inside: `409`, with its open ticket so staff can find it.

Request

``` code
POST /parking/entries HTTP/1.1
Content-Type: application/json

{
  "vehicleNumber": "MH12AB1234",
  "vehicleType": "CAR"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "This vehicle already has an open ticket.",
  "instance": "/parking/entries",
  "status": 409,
  "title": "Already parked",
  "ticketId": "ae866854-8cca-46ff-899c-a2008f7fff2f"
}
```

### Case 4: not a plate

**Why:** `400` before any slot is touched.

Request

``` code
POST /parking/entries HTTP/1.1
Content-Type: application/json

{
  "vehicleNumber": "12345",
  "vehicleType": "CAR"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Use a number plate like MH12AB1234.",
  "instance": "/parking/entries",
  "status": 400,
  "title": "Invalid vehicle number"
}
```

### Case 5: the car leaves

**Why:** a few seconds parked still pays the first hour: ₹40 (4000 paise). The slot goes back to the front of the free set.

Request

``` code
POST /parking/exits/ae866854-8cca-46ff-899c-a2008f7fff2f HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 218

{
  "ticketId": "ae866854-8cca-46ff-899c-a2008f7fff2f",
  "vehicleNumber": "MH12AB1234",
  "slotId": "F0-C01",
  "enteredAt": "2026-10-13T16:30:19Z",
  "exitedAt": "2026-10-13T16:30:19Z",
  "minutesParked": 0,
  "hoursCharged": 1,
  "feePaise": 4000
}
```

### Case 6: the exit gate retries

**Why:** the same receipt, word for word: no second charge, no second free slot.

Request

``` code
POST /parking/exits/ae866854-8cca-46ff-899c-a2008f7fff2f HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 218

{
  "ticketId": "ae866854-8cca-46ff-899c-a2008f7fff2f",
  "vehicleNumber": "MH12AB1234",
  "slotId": "F0-C01",
  "enteredAt": "2026-10-13T16:30:19Z",
  "exitedAt": "2026-10-13T16:30:19Z",
  "minutesParked": 0,
  "hoursCharged": 1,
  "feePaise": 4000
}
```

### Case 7: a ticket that does not exist

**Why:** `404`.

Request

``` code
POST /parking/exits/00000000-0000-0000-0000-000000000000 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No ticket has this id.",
  "instance": "/parking/exits/00000000-0000-0000-0000-000000000000",
  "status": 404,
  "title": "Ticket not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                             | What happens                            | Proved by                                               |
|------------------------------------------------------------------|-----------------------------------------|---------------------------------------------------------|
| Bike, then car, in an empty building                             | `F0-B01`, `F0-C01`                      | `theGarageGivesEachVehicleTheNearestSlotOfItsOwnType`   |
| A freed near slot                                                | Given to the next car                   | `carsFillTheNearestSlotsFirstAndAFreedNearSlotIsReused` |
| Plate with spaces, hyphen, lower case; then the same plate again | Normalised; `409` *Already parked*      | `spacesHyphensAndLowerCaseInThePlateAreTheSameCar`      |
| Bad plate, `TRUCK`, empty body                                   | `400`                                   | `badInputIs400`                                         |
| All 240 car slots taken                                          | Cars `409`; bikes still enter           | `whenCarSlotsRunOutCarsGet409ButBikesStillEnter`        |
| 150 minutes                                                      | 3 hours, ₹100                           | `exitChargesEveryStartedHour`                           |
| 12-minute bike stay                                              | 1 hour, ₹20                             | `aShortBikeStayPaysTheFirstHour`                        |
| 0, 1, 60, 60:01, 120, 121 minutes                                | 1, 1, 1, 2, 2, 3 hours                  | `everyStartedHourCounts`                                |
| 119 minutes                                                      | 2 hours (integer division would give 1) | `integerDivisionWouldHaveRoundedDown`                   |
| Exit twice, 5 hours apart                                        | Same receipt; slot freed once           | `exitingTwiceReturnsTheSameReceiptAndFreesTheSlotOnce`  |
| Same car returns after leaving                                   | New ticket                              | `theSameCarCanParkAgainAfterLeaving`                    |
| Unknown or malformed ticket                                      | `404`; `400`                            | `anUnknownOrMalformedTicketIsRefused`                   |

## The trap

Plausible but wrong

Re-scanning every slot on each entry instead of keeping free slots ordered.

"Loop over the slots, take the first free one" is the first idea, and it works in a demo with 10 slots. The first test runs it on the real 360-slot sheet, which lists floor 5 first: the bike gets a car slot on the top floor, the car walks 412 m instead of 6 m, and filling the building looks at 64,980 slots. The second test sends the same two vehicles to the real gate: `F0-B01` and `F0-C01`. Rounding the fee down instead of up was tried while building: 4 tests went red.

``` code
package com.parkora.parking;

import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * An empty building; a bike arrives, then a car.
 */
class RescanEverySlotTrapTest extends ApiTest {

    /** The "before" allocator: walk the slot sheet from the top and take the first free slot. Kept only in tests. */
    static class OldAllocator {
        final List<Slot> sheet = Garage.layout();
        final Set<String> taken = new HashSet<>();
        int slotsLookedAt;

        Slot allocate() {
            for (Slot s : sheet) {
                slotsLookedAt++;
                if (taken.add(s.id())) {
                    return s;
                }
            }
            return null;
        }
    }

    @Test
    void scanningTheSheetSendsTheBikeToACarSlotOnTheTopFloor() {
        OldAllocator old = new OldAllocator();
        Slot forBike = old.allocate();
        Slot forCar = old.allocate();
        assertThat(forBike.type()).isEqualTo(SlotType.CAR);          // a bike in a car slot
        assertThat(forBike.floor()).isEqualTo(5);                     // on the top floor of an empty building
        assertThat(forCar.walkMetres()).isEqualTo(5 * 80 + 2 * 6);    // the car walks 412 m, not 6 m

        // and every entry re-reads the sheet: filling the building looks at 360 + 359 + ... + 1 slots
        for (int i = 2; i < 360; i++) {
            old.allocate();
        }
        assertThat(old.slotsLookedAt).isEqualTo(360 * 361 / 2);
    }

    @Test
    void theGarageGivesEachVehicleTheNearestSlotOfItsOwnType() throws Exception {
        enter("KA01AB0001", "BIKE").andExpect(jsonPath("$.slot.id").value("F0-B01"))
                .andExpect(jsonPath("$.slot.type").value("BIKE"));
        enter("KA01AB0002", "CAR").andExpect(jsonPath("$.slot.id").value("F0-C01"))
                .andExpect(jsonPath("$.slot.walkMetres").value(6));
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
./mvnw test                 # all 15 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. `Math.ceilDiv` needs Java 18 or later.

## Try it yourself

The body is in `docs/car.json`.

``` code
# Enter: expect 201 and "slot": {"id": "F0-C01", ...}
curl -i -X POST http://localhost:8080/parking/entries -H "Content-Type: application/json" -d "@docs/car.json"

# Exit: paste the ticketId; expect "feePaise": 4000
curl -i -X POST http://localhost:8080/parking/exits/PASTE-THE-TICKET-ID
```

Run the exit twice and compare the two receipts.

## Troubleshooting

| You see                            | Cause                          | Fix                                                      |
|------------------------------------|--------------------------------|----------------------------------------------------------|
| `400` for `"vehicleType": "car"`   | Enum names are upper case.     | Send `CAR` or `BIKE`.                                    |
| `409 Already parked`               | That plate has an open ticket. | Exit it first, or use another plate.                     |
| `release version 25 not supported` | Maven is using an older JDK.   | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/011-smart-parking-slot-allocation/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/parkora/parking/
│   ├── ParkingController.java   ├── Garage.java      ├── Fee.java
│   ├── VehicleType.java         ├── SlotType.java    ├── Slot.java
│   ├── Ticket.java, Receipt.java, ApiErrors.java, ParkingApplication.java
├── src/test/java/com/parkora/parking/   (see Tests; TestClock moves time)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/parkora/parking/ParkingController.java`

Does  
Two gates. Normalises and checks the plate; maps each garage exception to its status.

Why  
HTTP stays out of the garage, which only knows slots and tickets.

Without it  
No API.

#### `src/main/java/com/parkora/parking/Garage.java`

Does  
Owns the building: one `TreeSet` of free slots per type, the tickets, the receipts.

Why  
The sorted sets make "nearest free slot" one `pollFirst`, and "free it again" one `add`.

Without it  
The trap: a loop over every slot, on every entry.

- `synchronized`: two gates at the same moment cannot take the same slot.
- A stored receipt makes a repeated exit harmless.
- `layout()` lists the building top floor first, as the old sheet did; the sorted set does not care.

#### `src/main/java/com/parkora/parking/VehicleType.java`

Does  
An enum whose values carry their slot type and rates.

Why  
Add a vehicle type in one place, with its own rules.

Without it  
Rates and slot rules spread over `if`s.

#### `src/main/java/com/parkora/parking/Fee.java`

Does  
Started hours and the fee, as plain arithmetic.

Why  
Tested without Spring, boundary by boundary.

Without it  
Rounding hidden inside the garage.

- `Math.ceilDiv(seconds, 3600)` rounds up; `seconds / 3600` would round down.

#### `src/main/java/com/parkora/parking/Slot.java`

A slot, and the comparator that defines "nearest".

#### `src/main/java/com/parkora/parking/SlotType.java`

Bike or car.

#### `src/main/java/com/parkora/parking/Ticket.java`

What the entry gate prints.

#### `src/main/java/com/parkora/parking/Receipt.java`

What the exit gate prints.

#### `src/main/java/com/parkora/parking/ParkingApplication.java`

Entry point, and the `Clock` bean the garage uses for "now".

#### `src/main/java/com/parkora/parking/ApiErrors.java`

Adds an `errors` map to validation failures (as in station 004).

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                    | Result |
|---------------|------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `ParkingContractTest` (10)    | pass   |
| Every station | Reproduce the failure before the fix     | `RescanEverySlotTrapTest` (2) | pass   |
| This station  | The tariff at every boundary             | `FeeTest` (3)                 | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.parkora.parking.RescanEverySlotTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0 -- in com.parkora.parking.ParkingContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.parkora.parking.FeeTest
[INFO] Tests run: 15, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/parkora/parking/RescanEverySlotTrapTest.java`

Written first: the old allocator's wrong slots and its 64,980 looks; the real gate's nearest slots.

#### `src/test/java/com/parkora/parking/ParkingContractTest.java`

Entry, reuse of freed slots, plates, a full building, fees, repeated exits.

#### `src/test/java/com/parkora/parking/FeeTest.java`

The tariff as plain arithmetic, at each boundary.

#### `src/test/java/com/parkora/parking/TestClock.java`

A clock the tests move forward: two hours pass in one line.

#### `src/test/java/com/parkora/parking/ApiTest.java`

Shared setup: the test clock replaces the real one; an empty building and a reset clock before each test.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/parkora/parking/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=AvailabilityBoardChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 15 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 20 tests pass (15 station tests and 5 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## The display board

Add `GET /parking/availability`: one entry per floor, ground floor first, with free car and bike slots.

**Done when:** both tests in `AvailabilityBoardChallengeTest` pass, and the station's tests still pass.

Hints

- The free sets already know every free slot and its floor.
- Read inside a `synchronized` method, so the board never shows a half-finished entry.

#### `challenge/AvailabilityBoardChallengeTest.java`

``` code
package com.parkora.parking;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: the display board at the gate: free slots per floor, per type. */
class AvailabilityBoardChallengeTest extends ApiTest {

    @Test
    void anEmptyBuildingShowsEveryFloorFull() throws Exception {
        mvc.perform(get("/parking/availability"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(6)))
                .andExpect(jsonPath("$[*].floor", contains(0, 1, 2, 3, 4, 5)))
                .andExpect(jsonPath("$[0].freeCarSlots").value(40))
                .andExpect(jsonPath("$[0].freeBikeSlots").value(20));
    }

    @Test
    void parkedVehiclesAreSubtractedFromTheirFloorAndType() throws Exception {
        enter("MH12AB0001", "CAR");
        enter("MH12AB0002", "CAR");
        String bike = ticketOf(enter("MH12AB0003", "BIKE"));
        exit(bike);
        mvc.perform(get("/parking/availability"))
                .andExpect(jsonPath("$[0].freeCarSlots").value(38))
                .andExpect(jsonPath("$[0].freeBikeSlots").value(20))
                .andExpect(jsonPath("$[1].freeCarSlots").value(40));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## A daily cap

Customers who park all day complain. Cap the fee: each full 24 hours costs at most ₹300 for a car and ₹150 for a bike; the hours after the last full day are charged normally, but never more than one more cap.

**Done when:** all three tests in `DailyCapChallengeTest` pass.

Hints

- Give each `VehicleType` a `dailyCapPaise`: the enum already holds the other rates.
- `Duration.toDays()` gives the full days; subtract them to get the rest.
- Exactly 24 hours is one cap, not one cap plus a first hour.

#### `challenge/DailyCapChallengeTest.java`

``` code
package com.parkora.parking;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: a daily cap. Each full 24 hours costs at most the cap (car Rs 300, bike Rs 150); the hours after
 * the last full day are charged normally, but never more than one more cap.
 */
class DailyCapChallengeTest {

    @Test
    void aShortStayIsUnchanged() {
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(2))).isEqualTo(7_000);
    }

    @Test
    void aLongDayStopsAtTheCap() {
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(10))).isEqualTo(30_000); // 31,000 without the cap
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(24))).isEqualTo(30_000);
    }

    @Test
    void theNextDayStartsCountingAgain() {
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(25))).isEqualTo(30_000 + 4_000);
        assertThat(Fee.feePaise(VehicleType.BIKE, Duration.ofHours(30))).isEqualTo(15_000 + 2_000 + 5 * 1_000);
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(48))).isEqualTo(60_000);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Five buildings, one app

Parkora now runs five buildings and wants an app to show free slots and reserve one for 15 minutes. Where does the free-slot state live when several servers run the gates? What happens to a reservation that is never used? How do you stop two app users reserving the last slot?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the scanning allocator picks wrong slots and does quadratic work.
2.  Model slots, slot types and vehicle types (with rates) as records and enums.
3.  Keep one `TreeSet` per slot type, ordered by walk then id.
4.  Entry: `pollFirst`; exit: store the receipt, `add` the slot back.
5.  Inject a `Clock`; test fees at every boundary.

## Design alternatives and trade-offs

| Approach                                        | What it costs                                                                             | Verdict          |
|-------------------------------------------------|-------------------------------------------------------------------------------------------|------------------|
| `TreeSet` per slot type                         | O(log n) take and return; can also remove a specific slot (for maintenance).              | Chosen           |
| `PriorityQueue` per slot type                   | Same take and return cost; removing a specific slot is O(n), and duplicates are possible. | Possible         |
| Scan every slot per entry                       | Wrong slots unless you also sort; O(n) per entry, O(n²) to fill (the trap).               | Wrong            |
| Bikes may use car slots when bike slots run out | More bikes in, fewer cars later. A business choice, not a technical one.                  | Ask the business |
| Read `Instant.now()` directly                   | Tests must wait real hours, or never test fees.                                           | Untestable       |

## Database design

None in this station. In a database, "nearest free slot" becomes `SELECT … WHERE type = ? AND free ORDER BY walk_metres LIMIT 1 FOR UPDATE SKIP LOCKED`, with an index on `(type, free, walk_metres)`; later stations cover row locks.

# 3 · Go deeper: Production

Concurrency  
One lock around the garage is right for one building on one server. Several servers need the database to decide (row locks).

Reliability  
Gates retry; the stored receipt makes exits safe to repeat. Entries are not: a retried entry for the same plate gets `409` with the open ticket, which the gate can print again.

Money  
Fees are whole paise. Rounding rules are written as tests, because customers read receipts closely.

Maintainability  
A new vehicle type is one enum value with its rates and slot type.

# 3 · Go deeper: Interview

## Interview takeaways

How would you find the nearest free slot quickly?

Keep free slots in a sorted structure (TreeSet or PriorityQueue) ordered by distance. Taking the nearest is O(log n), and freeing a slot puts it back in order. Scanning all slots per entry is O(n), and O(n²) to fill the building.

TreeSet or PriorityQueue?

Both give the smallest item in O(log n). TreeSet also removes any specific item in O(log n) and refuses duplicates; PriorityQueue's remove(Object) is O(n). TreeSet treats items its comparator calls equal as duplicates, so the comparator needs a tie-breaker.

How do you round 61 minutes up to 2 hours?

Math.ceilDiv(seconds, 3600), or (seconds + 3599) / 3600. Plain integer division rounds down. Test 60:00 and 60:01.

Why inject a Clock?

Code that calls Instant.now() cannot be tested at 'two hours later' without waiting. With a Clock bean, tests use a clock they move forward.

Why put rates on the enum?

Each vehicle type's data and rules live with it. Adding a type is one line, and switch statements cannot forget a rate.

## Self-check rubric

| Area        | Meets the bar                                  | Above the bar                                              |
|-------------|------------------------------------------------|------------------------------------------------------------|
| Correctness | All 15 tests pass.                             | You can name the boundary each fee test guards.            |
| Design      | Sorted free slots per type; rates on the enum. | You can argue TreeSet against PriorityQueue.               |
| Tests       | Time moves with a test clock.                  | You added a test for midnight or a daylight-saving change. |
| Explanation | You can draw the two sets and one entry.       | You can sketch the database version.                       |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on allocation code:

- Does anything loop over every item to find the best one, on every request?
- Does every sort have a tie-breaker?
- Is "now" injected, or read directly?
- Is every rounding rule pinned by a test at its boundary?
