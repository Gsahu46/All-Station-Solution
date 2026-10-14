package com.paysetu.payments;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@RestController
class PaymentIntentController {

    /** Banks offered for net banking in this demo. */
    static final Set<String> BANKS = Set.of("HDFC", "ICIC", "SBIN", "UTIB", "KKBK");

    record IntentRequest(@NotNull @Pattern(regexp = "[A-Za-z0-9_-]{1,40}") String orderId,
                         @NotNull @Min(100) @Max(value = 10_000_000, message = "must be at most Rs 1,00,000 (a demo rule)") Long amountPaise,
                         @NotNull @Valid PaymentMethod method) {
    }

    record Intent(String id, String orderId, long amountPaise, String status, PaymentMethod method,
                  Methods.NextAction nextAction, String refundRoute) {
    }

    /** Challenge 1: intents kept in memory, so they can be read back. Gone when the app stops. */
    private final Map<String, Intent> intents = new ConcurrentHashMap<>();

    /** Builds the intent, keeps it, and says what the payer does next. */
    @PostMapping("/payment-intents")
    ResponseEntity<Intent> create(@Valid @RequestBody IntentRequest r) {
        if (r.method() instanceof PaymentMethod.NetBanking(String bank) && !BANKS.contains(bank)) {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT,
                    "Net banking with bank " + bank + " is not available. Available: " + String.join(", ", BANKS.stream().sorted().toList()) + ".");
            p.setTitle("Bank not available");
            throw new ErrorResponseException(HttpStatus.UNPROCESSABLE_CONTENT, p, null);
        }
        String amount = "Rs " + r.amountPaise() / 100 + "." + String.format("%02d", r.amountPaise() % 100);
        Intent intent = new Intent("pi_" + UUID.randomUUID().toString().replace("-", ""), r.orderId(), r.amountPaise(), "REQUIRES_ACTION",
                r.method(), Methods.nextAction(r.method(), amount), Methods.refundRoute(r.method()));
        intents.put(intent.id(), intent);
        return ResponseEntity.created(URI.create("/payment-intents/" + intent.id())).body(intent);
    }

    @GetMapping("/payment-intents/{id}")
    Intent read(@PathVariable String id) {
        Intent intent = intents.get(id);
        if (intent == null) {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No payment intent has this id.");
            p.setTitle("Payment intent not found");
            throw new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        }
        return intent;
    }
}
