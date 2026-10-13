package com.seatsure.registrations;

import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Component
class RegistrationStore {

    private final Set<String> events = Set.of("pune-tech-summit-2026", "goa-food-fest-2026");
    private final Map<UUID, Registration> registrations = new ConcurrentHashMap<>();
    /** Challenge 1: "event + lower-case email" -> registration id. putIfAbsent claims a key atomically. */
    private final Map<String, UUID> byEmail = new ConcurrentHashMap<>();

    boolean eventExists(String eventId) {
        return events.contains(eventId);
    }

    Registration save(String eventId, RegistrationRequest r) {
        return store(UUID.randomUUID(), eventId, r);
    }

    /**
     * Challenge 1. Two requests with the same email at the same moment cannot both win: putIfAbsent is one atomic step.
     * (Check with containsKey, then put, and both could pass.) Locale.ROOT, so the server's language never changes the key.
     */
    Optional<Registration> saveIfNew(String eventId, RegistrationRequest r) {
        UUID id = UUID.randomUUID();
        if (byEmail.putIfAbsent(eventId + " " + r.email().toLowerCase(Locale.ROOT), id) != null) {
            return Optional.empty();
        }
        return Optional.of(store(id, eventId, r));
    }

    private Registration store(UUID id, String eventId, RegistrationRequest r) {
        var saved = new Registration(id, eventId, r.name(), r.email(), r.phone(), r.tickets(),
                Instant.now().truncatedTo(ChronoUnit.MILLIS));
        registrations.put(id, saved);
        return saved;
    }

    Optional<Registration> find(String eventId, UUID id) {
        return Optional.ofNullable(registrations.get(id)).filter(r -> r.eventId().equals(eventId));
    }

    /** Challenge 2: one event's registrations, oldest first. */
    List<Registration> forEvent(String eventId) {
        return registrations.values().stream()
                .filter(r -> r.eventId().equals(eventId))
                .sorted(Comparator.comparing(Registration::registeredAt).thenComparing(Registration::id))
                .toList();
    }

    int count() {
        return registrations.size();
    }
}
