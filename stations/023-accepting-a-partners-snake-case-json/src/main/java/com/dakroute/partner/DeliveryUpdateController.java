package com.dakroute.partner;

import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.ZoneId;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@RestController
class DeliveryUpdateController {

    private static final Logger log = LoggerFactory.getLogger(DeliveryUpdateController.class);

    /** The partner contract says event times are India time. The JSON cannot say it, so the code must. */
    static final ZoneId PARTNER_ZONE = ZoneId.of("Asia/Kolkata");

    record Accepted(boolean accepted, TrackingEvent event) {
    }

    /** Shipments we booked with this partner (demo data), and the events received for each. */
    private final Map<String, List<TrackingEvent>> shipments = new ConcurrentHashMap<>(Map.of(
            "DKR100000001IN", new CopyOnWriteArrayList<>(), "DKR100000002IN", new CopyOnWriteArrayList<>()));

    @PostMapping("/partner/delivery-updates")
    @ResponseStatus(HttpStatus.ACCEPTED)
    Accepted update(@Valid @RequestBody PartnerUpdate u) {
        String awb = u.awbNumber().toUpperCase(Locale.ROOT);
        List<TrackingEvent> events = shipments.get(awb);
        if (events == null) {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No shipment with this AWB was booked with us.");
            p.setTitle("Unknown AWB");
            throw new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        }
        TrackingEvent.Status status = TrackingEvent.Status.fromPartner(u.statusCode().toUpperCase(Locale.ROOT));
        if (status == TrackingEvent.Status.UNKNOWN) {
            log.warn("Partner sent a status code we do not map yet: {}", u.statusCode());   // kept, and visible to fix
        }
        TrackingEvent event = new TrackingEvent(awb, status, u.statusCode(), u.eventTime().atZone(PARTNER_ZONE).toInstant(),
                u.location() == null ? null : u.location().cityName(), u.location() == null ? null : u.location().pinCode(),
                u.promisedBy());
        events.add(event);
        return new Accepted(true, event);
    }
}
