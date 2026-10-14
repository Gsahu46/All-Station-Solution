package com.dakroute.tracking;

import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.Locale;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

@RestController
class ShipmentController {

    private static final Logger log = LoggerFactory.getLogger(ShipmentController.class);

    private final Shipments shipments;
    private final MeterRegistry metrics;
    private final ThreadPoolTaskExecutor etaExecutor;

    ShipmentController(Shipments shipments, MeterRegistry metrics, ThreadPoolTaskExecutor etaExecutor) {
        this.shipments = shipments;
        this.metrics = metrics;
        this.etaExecutor = etaExecutor;
    }

    /** Challenge 2: the estimate is worked out on a worker thread (simulated: delivered or out for delivery means today). */
    @GetMapping("/shipments/{awb}/eta")
    Map<String, String> eta(@PathVariable String awb) {
        Shipments.Shipment s = shipment(awb);
        String estimate = CompletableFuture.supplyAsync(() -> {
            String e = s.status().equals("OUT_FOR_DELIVERY") || s.status().equals("DELIVERED") ? "TODAY" : "LATER";
            log.info("Estimated {}: {}", s.awb(), e);
            return e;
        }, etaExecutor).join();
        return Map.of("awb", s.awb(), "estimate", estimate);
    }

    /**
     * Log levels: DEBUG for detail nobody reads unless debugging, INFO for a normal lookup, WARN for something a
     * person should look at soon, ERROR for a failure that needs action now. The request id is added by the filter.
     */
    @GetMapping("/shipments/{awb}")
    Shipments.Shipment shipment(@PathVariable String awb) {
        String normalised = awb.toUpperCase(Locale.ROOT);
        if (!normalised.matches("[A-Z0-9]{10,20}")) {
            count("invalid");
            throw problem(HttpStatus.BAD_REQUEST, "Invalid AWB", "An AWB is 10 to 20 letters and digits.");
        }
        log.debug("Looking up {}", normalised);
        try {
            Shipments.Shipment s = shipments.find(normalised).orElseThrow(() -> {
                count("not_found");
                log.info("Tracking lookup for {}: not found", normalised);
                return problem(HttpStatus.NOT_FOUND, "Shipment not found", "No shipment has this AWB.");
            });
            count("found");
            log.info("Tracking lookup for {}: {}", normalised, s.status());
            return s;
        } catch (Shipments.StoreUnavailable e) {
            count("error");
            log.error("Tracking lookup for {} failed: {}", normalised, e.getMessage());
            ErrorResponseException unavailable = problem(HttpStatus.SERVICE_UNAVAILABLE, "Tracking unavailable",
                    "Tracking is not available right now. Try again in a minute.");
            unavailable.getHeaders().set("Retry-After", "60");
            throw unavailable;
        }
    }

    /** tracking.lookups{outcome=found|not_found|invalid|error}: the metric the alert watches. */
    private void count(String outcome) {
        metrics.counter("tracking.lookups", "outcome", outcome).increment();
    }

    /** Every problem carries the request id, so a customer's screenshot is enough to find the logs. */
    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        p.setProperty("requestId", MDC.get(RequestIdFilter.MDC_KEY));
        return new ErrorResponseException(status, p, null);
    }
}
