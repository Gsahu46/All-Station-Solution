package com.kartwala.refunds;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.List;
import java.util.Locale;

@RestController
class RefundController {

    /** tagsAttached is asked for clothing, sealIntact for electronics; otherwise they may be left out. */
    record CheckRequest(@NotNull @Pattern(regexp = "(?i)KW-\\d{4}", message = "must look like KW-1001") String orderId,
                        @NotNull Reason reason, Boolean tagsAttached, Boolean sealIntact) {
    }

    record CheckResponse(String orderId, boolean eligible, List<String> reasons, long refundPaise, LocalDate lastDayToReturn) {
    }

    private final RefundService service;

    RefundController(RefundService service) {
        this.service = service;
    }

    /** A check only: nothing is returned or refunded by calling it. */
    @PostMapping("/refund-eligibility-checks")
    CheckResponse check(@Valid @RequestBody CheckRequest request) {
        RefundRules.Decision d = service.check(request.orderId(), request.reason(), request.tagsAttached(), request.sealIntact());
        return new CheckResponse(request.orderId().toUpperCase(Locale.ROOT), d.eligible(), d.reasons(), d.refundPaise(), d.lastDayToReturn());
    }
}
