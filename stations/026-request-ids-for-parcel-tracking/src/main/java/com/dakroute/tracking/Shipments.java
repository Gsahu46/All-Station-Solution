package com.dakroute.tracking;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * The tracking store: demo shipments in memory. A real one is a database or another service, which can fail.
 * dakroute.tracking.simulate-outage=true makes every lookup fail, for the failure drill; it is off by default.
 */
@Component
class Shipments {

    record Event(Instant at, String status, String place) {
    }

    record Shipment(String awb, String status, String destinationCity, List<Event> events) {
    }

    static final class StoreUnavailable extends RuntimeException {
        StoreUnavailable() {
            super("tracking store did not answer (simulated outage)");
        }
    }

    private final Map<String, Shipment> byAwb = Map.of(
            "DKR100000001IN", new Shipment("DKR100000001IN", "OUT_FOR_DELIVERY", "Pune", List.of(
                    new Event(Instant.parse("2026-10-13T12:50:00Z"), "PICKED_UP", "Mumbai"),
                    new Event(Instant.parse("2026-10-14T03:45:00Z"), "OUT_FOR_DELIVERY", "Pune"))),
            "DKR100000002IN", new Shipment("DKR100000002IN", "DELIVERED", "Nagpur", List.of(
                    new Event(Instant.parse("2026-10-12T09:10:00Z"), "PICKED_UP", "Mumbai"),
                    new Event(Instant.parse("2026-10-14T06:30:00Z"), "DELIVERED", "Nagpur"))));

    private volatile boolean outage;

    Shipments(@Value("${dakroute.tracking.simulate-outage:false}") boolean outage) {
        this.outage = outage;
    }

    Optional<Shipment> find(String awb) {
        if (outage) {
            throw new StoreUnavailable();
        }
        return Optional.ofNullable(byAwb.get(awb));
    }

    /** For the drill test: start and end an outage without restarting. */
    void simulateOutage(boolean on) {
        outage = on;
    }
}
