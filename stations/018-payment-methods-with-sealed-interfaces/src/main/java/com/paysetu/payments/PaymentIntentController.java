package com.paysetu.payments;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Set;
import java.util.UUID;

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

    /** Builds the intent and says what the payer does next. Nothing is stored in this station (challenge 1 stores it). */
    @PostMapping("/payment-intents")
    @ResponseStatus(HttpStatus.CREATED)
    Intent create(@Valid @RequestBody IntentRequest r) {
        if (r.method() instanceof PaymentMethod.NetBanking(String bank) && !BANKS.contains(bank)) {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT,
                    "Net banking with bank " + bank + " is not available. Available: " + String.join(", ", BANKS.stream().sorted().toList()) + ".");
            p.setTitle("Bank not available");
            throw new ErrorResponseException(HttpStatus.UNPROCESSABLE_CONTENT, p, null);
        }
        String amount = "Rs " + r.amountPaise() / 100 + "." + String.format("%02d", r.amountPaise() % 100);
        return new Intent("pi_" + UUID.randomUUID().toString().replace("-", ""), r.orderId(), r.amountPaise(), "REQUIRES_ACTION",
                r.method(), Methods.nextAction(r.method(), amount), Methods.refundRoute(r.method()));
    }
}
