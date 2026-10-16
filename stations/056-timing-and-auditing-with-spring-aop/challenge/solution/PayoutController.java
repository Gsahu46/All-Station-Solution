package com.paysetu.payouts;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;
import java.util.Locale;

@RestController
class PayoutController {

    /** Demo limits: ₹1 to ₹10 lakh per payout. The IFSC shape is checked; whether the branch exists is not. */
    record NewPayout(@NotNull Long merchantId, @NotNull @Min(100) @Max(100_000_000) Long amountPaise,
                     @NotNull @Pattern(regexp = "(?i)[A-Z]{4}0[A-Z0-9]{6}") String ifsc,
                     @NotNull @Pattern(regexp = "[0-9]{9,18}") String accountNumber) {
    }

    private final PayoutService payouts;
    private final AuditLog auditLog;

    PayoutController(PayoutService payouts, AuditLog auditLog) {
        this.payouts = payouts;
        this.auditLog = auditLog;
    }

    /** Demo: unprotected. A real payout API needs the merchant's authentication and usually a second approval. */
    @PostMapping("/payouts")
    ResponseEntity<PayoutService.Payout> request(@Valid @RequestBody NewPayout body) {
        PayoutService.Payout p = payouts.request(body.merchantId(), body.amountPaise(), body.ifsc().toUpperCase(Locale.ROOT), body.accountNumber());
        return ResponseEntity.created(URI.create("/payouts/" + p.id())).body(p);
    }

    @PostMapping("/payouts/{id}/cancellation")
    PayoutService.Payout cancel(@PathVariable long id) {
        return payouts.cancel(id);
    }

    @GetMapping("/payouts/{id}")
    PayoutService.Payout get(@PathVariable long id) {
        return payouts.find(id).orElseThrow(() -> PayoutService.problem(HttpStatus.NOT_FOUND, "Payout not found", "No payout " + id + "."));
    }

    /** Newest first. Demo: unprotected; a real audit log is for staff only. */
    @GetMapping("/audit-events")
    List<AuditLog.AuditEvent> audit(@RequestParam(required = false) String action,
                                    @RequestParam(defaultValue = "20") @jakarta.validation.constraints.Min(1) @Max(100) int limit) {
        return auditLog.latest(action, limit);
    }
}
