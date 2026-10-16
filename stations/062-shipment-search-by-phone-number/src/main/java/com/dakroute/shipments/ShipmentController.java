package com.dakroute.shipments;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

@RestController
class ShipmentController {

    private final ShipmentSearch search;

    ShipmentController(ShipmentSearch search) {
        this.search = search;
    }

    /** Demo rule: at most 366 days per search, so one query never walks a customer's whole history. */
    @GetMapping("/shipments/search")
    ShipmentSearch.Result search(@RequestParam String phone,
                                 @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                 @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        if (to.isBefore(from) || ChronoUnit.DAYS.between(from, to) > 365) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "The dates must run forwards, at most 366 days");
        }
        return search.search(PhoneNumber.normalise(phone), from, to);
    }
}
