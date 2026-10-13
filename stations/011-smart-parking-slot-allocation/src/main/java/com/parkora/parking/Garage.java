package com.parkora.parking;

import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.UUID;

/**
 * The building: 6 floors (0 to 5), each with 40 car slots and 20 bike slots.
 *
 * Free slots are kept already ordered, nearest first, in one TreeSet per slot type. Entry takes the first one
 * (pollFirst, O(log n)); exit puts the slot back (add, O(log n)). Nothing ever scans all 360 slots.
 * Every public method is synchronized: two cars at two gates must never get the same slot.
 */
@Component
class Garage {

    static final int FLOORS = 6, CAR_SLOTS_PER_FLOOR = 40, BIKE_SLOTS_PER_FLOOR = 20;

    static class GarageFull extends RuntimeException {
    }

    static class AlreadyParked extends RuntimeException {
        final UUID ticketId;

        AlreadyParked(UUID ticketId) {
            this.ticketId = ticketId;
        }
    }

    static class TicketNotFound extends RuntimeException {
    }

    private final Clock clock;
    private final Map<SlotType, TreeSet<Slot>> free = new EnumMap<>(SlotType.class);
    private final Map<UUID, Ticket> tickets = new HashMap<>();
    private final Map<UUID, Receipt> receipts = new HashMap<>();
    private final Map<String, UUID> parkedNow = new HashMap<>(); // vehicle number -> open ticket

    Garage(Clock clock) {
        this.clock = clock;
        reset();
    }

    /** The whole layout, in the order a builder would list it. Package-private so the trap test can scan it. */
    static List<Slot> layout() {
        List<Slot> slots = new ArrayList<>();
        for (int floor = FLOORS - 1; floor >= 0; floor--) { // listed top floor first, as the building's old sheet was
            for (int n = 1; n <= CAR_SLOTS_PER_FLOOR; n++) {
                slots.add(new Slot("F%d-C%02d".formatted(floor, n), floor, n, SlotType.CAR, floor * 80 + n * 6));
            }
            for (int n = 1; n <= BIKE_SLOTS_PER_FLOOR; n++) {
                slots.add(new Slot("F%d-B%02d".formatted(floor, n), floor, n, SlotType.BIKE, floor * 80 + n * 3));
            }
        }
        return slots;
    }

    synchronized Ticket enter(String vehicleNumber, VehicleType type) {
        UUID open = parkedNow.get(vehicleNumber);
        if (open != null) {
            throw new AlreadyParked(open);
        }
        Slot slot = free.get(type.slotType).pollFirst(); // the nearest free slot of the right type, or null
        if (slot == null) {
            throw new GarageFull();
        }
        Ticket t = new Ticket(UUID.randomUUID(), vehicleNumber, type, slot, now());
        tickets.put(t.ticketId(), t);
        parkedNow.put(vehicleNumber, t.ticketId());
        return t;
    }

    /** Exiting twice (a retry at the gate) returns the first receipt: no second charge, no second free slot. */
    synchronized Receipt exit(UUID ticketId) {
        Receipt earlier = receipts.get(ticketId);
        if (earlier != null) {
            return earlier;
        }
        Ticket t = tickets.get(ticketId);
        if (t == null) {
            throw new TicketNotFound();
        }
        Instant out = now();
        Duration parked = Duration.between(t.enteredAt(), out);
        Receipt r = new Receipt(t.ticketId(), t.vehicleNumber(), t.slot().id(), t.enteredAt(), out,
                parked.toMinutes(), Fee.hoursCharged(parked), Fee.feePaise(t.vehicleType(), parked));
        receipts.put(ticketId, r);
        parkedNow.remove(t.vehicleNumber());
        free.get(t.slot().type()).add(t.slot()); // back in order: the next car may get it if it is the nearest
        return r;
    }

    synchronized int freeCount(SlotType type) {
        return free.get(type).size();
    }

    /** Empty building. Used at start-up, and by tests so each one starts clean. */
    synchronized void reset() {
        free.clear();
        for (SlotType t : SlotType.values()) {
            free.put(t, new TreeSet<>(Slot.NEAREST_FIRST));
        }
        layout().forEach(s -> free.get(s.type()).add(s));
        tickets.clear();
        receipts.clear();
        parkedNow.clear();
    }

    private Instant now() {
        return clock.instant().truncatedTo(ChronoUnit.SECONDS);
    }
}
