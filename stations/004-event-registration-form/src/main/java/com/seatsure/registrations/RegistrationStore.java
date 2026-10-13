package com.seatsure.registrations;

import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Events and registrations, in memory: everything is lost on restart. A database comes in later stations.
 * ConcurrentHashMap because two people can register at the same moment on different server threads.
 */
@Component
class RegistrationStore {

    private final Set<String> events = Set.of("pune-tech-summit-2026", "goa-food-fest-2026");
    private final Map<UUID, Registration> registrations = new ConcurrentHashMap<>();

    boolean eventExists(String eventId) {
        return events.contains(eventId);
    }

    Registration save(String eventId, RegistrationRequest r) {
        var saved = new Registration(UUID.randomUUID(), eventId, r.name(), r.email(), r.phone(), r.tickets(),
                Instant.now().truncatedTo(ChronoUnit.MILLIS));
        registrations.put(saved.id(), saved);
        return saved;
    }

    /** A registration is found only under its own event: /events/A/registrations/{id of a B registration} is a 404. */
    Optional<Registration> find(String eventId, UUID id) {
        return Optional.ofNullable(registrations.get(id)).filter(r -> r.eventId().equals(eventId));
    }

    int count() {
        return registrations.size();
    }
}
