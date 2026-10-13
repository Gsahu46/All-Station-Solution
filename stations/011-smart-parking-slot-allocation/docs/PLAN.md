# Station 011 plan: Smart parking slot allocation

**Problem.** Parkora's gate takes the first free slot on a top-floor-first sheet, any size: far walks, bikes in car
slots, and a full scan per entry.

**Endpoints.** `POST /parking/entries` 201 ticket / 400 / 409 no free slot / 409 already parked;
`POST /parking/exits/{ticketId}` 200 receipt (repeat returns the same receipt) / 404 / 400.

**Data.** No database. 6 floors x (40 car + 20 bike). Free slots: EnumMap<SlotType, TreeSet<Slot>> nearest first
(walk then id). VehicleType enum carries slot type and rates. Fee: every started hour (Math.ceilDiv), paise.
Clock bean; tests use TestClock.

**Trap.** Re-scanning the slot sheet. `RescanEverySlotTrapTest`: bike to a top-floor car slot, car 412 m away,
64,980 slot looks to fill; real gate gives F0-B01 / F0-C01. Mutation: floor division in Fee -> 4 tests red.

**Tests.** Trap, `ParkingContractTest`, `FeeTest`.

**Practice.** 1: availability board per floor. 2: daily cap per 24 hours. Design: five buildings and reservations.
