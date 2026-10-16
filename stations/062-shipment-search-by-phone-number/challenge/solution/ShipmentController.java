package com.dakroute.shipments;

import jakarta.validation.constraints.Pattern;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.Locale;
import java.util.Map;

@RestController
class ShipmentController {

    private final ShipmentSearch search;

    ShipmentController(ShipmentSearch search) {
        this.search = search;
    }

    @GetMapping("/shipments/{awb}")
    ShipmentSearch.Shipment byAwb(@PathVariable @Pattern(regexp = "(?i)DR[0-9]{10}") String awb) {
        String normalised = awb.toUpperCase(Locale.ROOT);
        return search.byAwb(normalised).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No shipment " + normalised));
    }

    @GetMapping("/shipments/summary")
    Map<String, Long> summary(@RequestParam String phone,
                              @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                              @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        checkRange(from, to);
        return search.summary(PhoneNumber.normalise(phone), from, to);
    }

    private static void checkRange(LocalDate from, LocalDate to) {
        if (to.isBefore(from) || ChronoUnit.DAYS.between(from, to) > 365) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "The dates must run forwards, at most 366 days");
        }
    }

    /** Demo rule: at most 366 days per search, so one query never walks a customer's whole history. */
    @GetMapping("/shipments/search")
    ShipmentSearch.Result search(@RequestParam String phone,
                                 @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                 @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        checkRange(from, to);
        return search.search(PhoneNumber.normalise(phone), from, to);
    }
}
