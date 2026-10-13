package com.rydo.fares;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.List;

/**
 * Takes only where the ride starts and ends. Distance and prices are worked out here, never read from the request:
 * a client that could send "distanceKm=1" or "fare=10" could set its own price.
 */
@RestController
class FareEstimateController {

    record Estimate(VehicleType vehicle, long farePaise) {
    }

    record Estimates(Location pickup, Location drop, BigDecimal distanceKm, List<Estimate> estimates) {
    }

    @GetMapping("/fare-estimates")
    Estimates estimate(@RequestParam String pickup, @RequestParam String drop) {
        Location from = location("pickup", pickup), to = location("drop", drop);
        BigDecimal km = Location.roadKm(from, to);
        // Polymorphism: every vehicle type is asked the same question; none of them is special-cased here.
        List<Estimate> estimates = Arrays.stream(VehicleType.values())
                .map(v -> new Estimate(v, v.farePaise(km)))
                .toList();
        return new Estimates(from, to, km, estimates);
    }

    private static Location location(String name, String text) {
        Location l;
        try {
            l = Location.parse(text);
        } catch (IllegalArgumentException e) {
            throw problem(HttpStatus.BAD_REQUEST, "Invalid location", "'" + name + "' must be latitude,longitude, like 12.9756,77.6066.");
        }
        if (!l.inServiceArea()) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Outside service area", "'" + name + "' is outside the area Rydo serves.");
        }
        return l;
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
