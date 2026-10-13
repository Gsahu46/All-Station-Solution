package com.fitnest.classes;

import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.temporal.ChronoUnit;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/**
 * Classes, members and bookings, in memory. Every method that reads or changes bookings is synchronized:
 * "count the bookings, then add one" must not interleave with another request, or a class of 2 could get 3.
 * (One lock is fine for one gym in memory; a database does this with constraints and transactions in later stations.)
 */
@Component
class ClassSchedule {

    private static final LocalDate MON = LocalDate.of(2026, 10, 19);
    /** Challenge 2: capacity can change, so the map must accept updates (all access is synchronized). */
    private final Map<Long, GymClass> classes = new HashMap<>(Map.of(
            1L, new GymClass(1, "Morning Yoga", "Kavya", MON, LocalTime.of(6, 30), 2, 0),
            2L, new GymClass(2, "HIIT Blast", "Arjun", MON, LocalTime.of(7, 30), 20, 0),
            3L, new GymClass(3, "Zumba", "Kavya", MON, LocalTime.of(18, 0), 15, 0),
            4L, new GymClass(4, "Pilates", "Meher", MON.plusDays(1), LocalTime.of(7, 0), 10, 0)));
    private final Set<Long> members = Set.of(101L, 102L, 103L);
    private final Map<UUID, Booking> bookings = new LinkedHashMap<>();

    synchronized List<GymClass> on(LocalDate date) {
        return classes.values().stream()
                .filter(c -> c.date().equals(date))
                .sorted(Comparator.comparing(GymClass::startTime))
                .map(c -> c.withSpotsLeft(c.capacity() - booked(c.id())))
                .toList();
    }

    boolean memberExists(long memberId) {
        return members.contains(memberId);
    }

    synchronized BookingOutcome book(long classId, long memberId) {
        GymClass c = classes.get(classId);
        if (c == null) {
            return new BookingOutcome.ClassNotFound();
        }
        Optional<Booking> existing = bookings.values().stream()
                .filter(b -> b.classId() == classId && b.memberId() == memberId).findFirst();
        if (existing.isPresent()) {
            return new BookingOutcome.AlreadyBooked(existing.get().id());
        }
        if (booked(classId) >= c.capacity()) {
            return new BookingOutcome.ClassFull();
        }
        Booking b = new Booking(UUID.randomUUID(), classId, memberId, Instant.now().truncatedTo(ChronoUnit.MILLIS));
        bookings.put(b.id(), b);
        return new BookingOutcome.Booked(b);
    }

    synchronized Optional<Booking> booking(UUID id) {
        return Optional.ofNullable(bookings.get(id));
    }

    /** True if a booking was removed; false if there was none with this id. */
    synchronized boolean cancel(UUID id) {
        return bookings.remove(id) != null;
    }

    synchronized List<Booking> forMember(long memberId) {
        return bookings.values().stream().filter(b -> b.memberId() == memberId).toList();
    }

    /** Challenge 1: one class's bookings, in the order they were made (the map keeps insertion order). */
    synchronized Optional<List<Booking>> roster(long classId) {
        if (!classes.containsKey(classId)) {
            return Optional.empty();
        }
        return Optional.of(bookings.values().stream().filter(b -> b.classId() == classId).toList());
    }

    /** Challenge 2. The outcome, not a status code: the controller decides what each one means in HTTP. */
    enum CapacityChange { UPDATED, CLASS_NOT_FOUND, BELOW_BOOKINGS }

    synchronized CapacityChange setCapacity(long classId, int capacity) {
        GymClass c = classes.get(classId);
        if (c == null) {
            return CapacityChange.CLASS_NOT_FOUND;
        }
        if (capacity < booked(classId)) {
            return CapacityChange.BELOW_BOOKINGS;
        }
        classes.put(classId, new GymClass(c.id(), c.name(), c.trainer(), c.date(), c.startTime(), capacity, 0));
        return CapacityChange.UPDATED;
    }

    synchronized Optional<GymClass> find(long classId) {
        return Optional.ofNullable(classes.get(classId)).map(c -> c.withSpotsLeft(c.capacity() - booked(c.id())));
    }

    /** For tests only: start each test from an empty booking list. */
    synchronized void clearBookings() {
        bookings.clear();
    }

    private int booked(long classId) {
        return (int) bookings.values().stream().filter(b -> b.classId() == classId).count();
    }
}
