package com.teamdesk.holidays;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientException;

import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;
import java.time.LocalDate;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@RestController
class HolidayController {

    private static final Logger log = LoggerFactory.getLogger(HolidayController.class);

    /** States Teamdesk has offices in (a demo list). */
    static final Set<String> STATES = Set.of("KA", "MH", "DL", "TN");

    record Holiday(LocalDate date, String name, String type) {
    }

    /** Challenge 1: source is "provider" for a fresh answer, "cache" for the last good one. */
    record Holidays(int year, String state, List<Holiday> holidays, String source) {
    }

    /** Challenge 1: the last good answer per year and state. A year's holidays rarely change. */
    private final Map<String, List<Holiday>> lastGood = new ConcurrentHashMap<>();

    private final HolidayProviderClient provider;

    HolidayController(HolidayProviderClient provider) {
        this.provider = provider;
    }

    @GetMapping("/holidays")
    Holidays holidays(@RequestParam @Min(2000) @Max(2100) int year, @RequestParam String state) {
        String region = state.toUpperCase(Locale.ROOT);
        if (!STATES.contains(region)) {
            throw problem(HttpStatus.BAD_REQUEST, "Unknown state", "state must be one of " + String.join(", ", STATES.stream().sorted().toList()) + ".");
        }
        String key = year + "/" + region;
        try {
            List<Holiday> fresh = call(year, region).holidays().stream()
                    .map(h -> new Holiday(h.date(), h.name(), h.type()))
                    .sorted(Comparator.comparing(Holiday::date))
                    .toList();
            lastGood.put(key, fresh);
            return new Holidays(year, region, fresh, "provider");
        } catch (ErrorResponseException failure) {
            List<Holiday> cached = lastGood.get(key);
            if (cached == null || failure.getStatusCode().value() == 404) {
                throw failure;
            }
            log.warn("Serving the last good holiday list for {} instead of: {}", key, failure.getBody().getTitle());
            return new Holidays(year, region, cached, "cache");
        }
    }

    /**
     * Every way the provider can fail, translated into our own answer. The provider's error body is logged, never
     * passed on: it may name internal hosts or keys, and our clients cannot act on it anyway.
     */
    private HolidayProviderClient.ProviderResponse call(int year, String region) {
        try {
            HolidayProviderClient.ProviderResponse answer = provider.holidays(year, region);
            if (answer == null || answer.holidays() == null) {
                throw new RestClientException("empty answer");
            }
            return answer;
        } catch (HttpClientErrorException.NotFound e) {
            throw problem(HttpStatus.NOT_FOUND, "No holiday list", "The provider has no holiday list for " + region + " in " + year + ".");
        } catch (ResourceAccessException e) {
            boolean timedOut = e.getCause() instanceof HttpTimeoutException || e.getCause() instanceof SocketTimeoutException;
            log.warn("Holiday provider unreachable ({}): {}", timedOut ? "timeout" : "connection", e.getMessage());
            throw timedOut
                    ? problem(HttpStatus.GATEWAY_TIMEOUT, "Holiday provider too slow", "The holiday provider did not answer in time. Try again shortly.")
                    : problem(HttpStatus.BAD_GATEWAY, "Holiday provider unreachable", "The holiday provider could not be reached. Try again shortly.");
        } catch (RestClientException e) {   // its 5xx, any other 4xx (our key or request is wrong), or a body we cannot read
            log.warn("Holiday provider failed: {}", e.getMessage());
            throw problem(HttpStatus.BAD_GATEWAY, "Holiday provider failed", "The holiday provider failed to answer. Try again shortly.");
        }
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
