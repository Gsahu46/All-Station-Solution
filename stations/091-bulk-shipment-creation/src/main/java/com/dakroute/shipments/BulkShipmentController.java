package com.dakroute.shipments;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
class BulkShipmentController {

    /** The list itself is checked here (present, 1 to 500). No @Valid on the items: each is checked on its own in BulkShipments. */
    record BulkRequest(@NotNull @Size(min = 1, max = BulkShipments.MAX_BATCH) List<BulkShipments.ShipmentRequest> shipments) {
    }

    private final BulkShipments bulk;

    BulkShipmentController(BulkShipments bulk) {
        this.bulk = bulk;
    }

    /**
     * 200 with a report, even when some items failed: the call worked, and each item says how it went. Not 207: that
     * status is WebDAV's (RFC 4918) and its clients expect an XML multistatus body.
     */
    @PostMapping("/shipments/bulk")
    BulkShipments.Report create(@Valid @RequestBody BulkRequest body) {
        return bulk.create(body.shipments());
    }
}
