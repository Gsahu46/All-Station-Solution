package com.mapwise.geocode;

import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;

@RestController
class GeocodeController {

    record Usage(long partnerId, String partner, int perSecond, int burst, long tokensLeft, int dailyQuota, int usedToday, Instant quotaResetsAt) {
    }

    private final Geocoder geocoder;
    private final RateLimiter limiter;

    GeocodeController(Geocoder geocoder, RateLimiter limiter) {
        this.geocoder = geocoder;
        this.limiter = limiter;
    }

    /** Printable text only: no line breaks or other control characters. */
    @GetMapping("/geocode")
    Geocoder.Place geocode(@RequestParam @Size(min = 3, max = 200) @Pattern(regexp = "[^\\p{Cntrl}]*") String address) {
        return geocoder.find(address).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No place found for this address."));
    }

    /** A partner's own limits and what is left. Another partner's id is a 403: ids are not secret, usage is. */
    @GetMapping("/partners/{id}/usage")
    Usage usage(@PathVariable long id, @RequestAttribute(ApiKeyFilter.PARTNER) Partners.Partner partner) {
        if (id != partner.id()) {
            throw problem(HttpStatus.FORBIDDEN, "A key can only read its own partner's usage.");
        }
        RateLimiter.Usage u = limiter.usage(partner);
        return new Usage(partner.id(), partner.name(), partner.perSecond(), partner.burst(), u.tokensLeft(), partner.dailyQuota(), u.usedToday(), u.quotaResetsAt());
    }

    private static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
