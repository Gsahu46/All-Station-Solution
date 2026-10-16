package com.basketo.inventory;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.PessimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

@RestController
class StockController {

    /** Demo limits: up to 1,000 SKUs per call, up to 1,000,000 units each. */
    record Line(@NotNull @Pattern(regexp = "[A-Za-z0-9-]{3,30}") String sku, @NotNull @Min(0) @Max(1_000_000) Integer quantity) {
    }

    record Snapshot(@NotNull @Size(min = 1, max = 1000) List<@NotNull @Valid Line> items) {
    }

    private static final Logger log = LoggerFactory.getLogger(StockController.class);

    private final StockSync sync;

    StockController(StockSync sync) {
        this.sync = sync;
    }

    /** PUT: the body is the warehouse's count for these SKUs. Sending it twice leaves the same rows. */
    @PutMapping("/warehouses/{id}/stock")
    StockSync.Synced put(@PathVariable long id, @Valid @RequestBody Snapshot body) {
        List<StockSync.Item> items = body.items().stream()
                .map(l -> new StockSync.Item(l.sku().toUpperCase(Locale.ROOT), l.quantity())).toList();
        Set<String> seen = new HashSet<>();
        for (StockSync.Item item : items) {
            if (!seen.add(item.sku())) {
                throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_CONTENT, "SKU " + item.sku() + " appears twice; which count is right?");
            }
        }
        // InnoDB may still pick a sync as a deadlock victim (error 1213); the whole snapshot rolled back, so run it again.
        for (int attempt = 1; ; attempt++) {
            try {
                return sync.sync(id, items);
            } catch (PessimisticLockingFailureException e) {
                log.warn("Stock sync of warehouse {} deadlocked (attempt {}): {}", id, attempt, e.getMostSpecificCause().getMessage());
                if (attempt == 3) {
                    throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Stock sync kept deadlocking; try again", e);
                }
            }
        }
    }
}
