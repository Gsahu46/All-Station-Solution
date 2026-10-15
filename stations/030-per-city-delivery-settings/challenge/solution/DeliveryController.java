package com.basketo.delivery;

import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

@RestController
class DeliveryController {

    record Terms(String city, double radiusKm, long feePaise, long minimumOrderPaise) {
    }

    /** No distance field: the client sends where the address is; the server works out how far it is. */
    record CheckRequest(@NotBlank String city, @NotNull @DecimalMin("-90") @DecimalMax("90") Double lat,
                        @NotNull @DecimalMin("-180") @DecimalMax("180") Double lon, @NotNull @Min(1) Long orderPaise) {
    }

    record Check(String city, double distanceKm, boolean deliverable, List<String> reasons, long feePaise,
                 long minimumOrderPaise, long orderPaise) {
    }

    private final DeliverySettings settings;
    private final DistanceCalculator distance;

    DeliveryController(DeliverySettings settings, DistanceCalculator distance) {
        this.settings = settings;
        this.distance = distance;
    }

    @GetMapping("/cities/{city}/delivery-terms")
    Terms terms(@PathVariable String city) {
        String key = city.toLowerCase(Locale.ROOT);
        DeliverySettings.City c = find(key);
        return new Terms(key, c.radiusKm(), c.feePaise(), c.minimumOrderPaise());
    }

    @PostMapping("/delivery-checks")
    Check check(@Valid @RequestBody CheckRequest r) {
        String key = r.city().toLowerCase(Locale.ROOT);
        DeliverySettings.City c = find(key);
        double km = distance.km(c.store(), r.lat(), r.lon());
        List<String> reasons = new ArrayList<>();
        if (km > c.radiusKm()) {
            reasons.add("OUT_OF_RANGE");
        }
        if (r.orderPaise() < c.minimumOrderPaise()) {
            reasons.add("BELOW_MINIMUM");
        }
        return new Check(key, Math.round(km * 100) / 100.0, reasons.isEmpty(), reasons, c.feeFor(km, r.orderPaise()),
                c.minimumOrderPaise(), r.orderPaise());
    }

    private DeliverySettings.City find(String city) {
        DeliverySettings.City c = settings.cities().get(city);
        if (c == null) {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "Basketo does not deliver in this city yet.");
            p.setTitle("City not served");
            throw new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        }
        return c;
    }
}
