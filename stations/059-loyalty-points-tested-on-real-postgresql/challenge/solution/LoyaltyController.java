package com.basketo.loyalty;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Locale;

@RestController
class LoyaltyController {

    /** Demo limits: an order up to ₹10 lakh; up to 100,000 points redeemed at once. */
    record Earn(@NotNull @Pattern(regexp = "[A-Za-z0-9-]{4,30}") String orderRef, @NotNull @Min(1) @Max(100_000_000) Long amountPaise) {
    }

    record Redeem(@NotNull @Min(1) @Max(100_000) Integer points) {
    }

    private final LoyaltyLedger ledger;

    LoyaltyController(LoyaltyLedger ledger) {
        this.ledger = ledger;
    }

    /** Demo: unprotected. In a shop, only the order system may call earn, after the order is paid. */
    @PostMapping("/loyalty/{customerId}/earn")
    @ResponseStatus(HttpStatus.CREATED)
    LoyaltyLedger.Earned earn(@PathVariable long customerId, @Valid @RequestBody Earn body) {
        return ledger.earn(customerId, body.orderRef().toUpperCase(Locale.ROOT), body.amountPaise());
    }

    @GetMapping("/loyalty/{customerId}")
    LoyaltyLedger.Statement statement(@PathVariable long customerId) {
        return ledger.statement(customerId);
    }

    @PostMapping("/loyalty/{customerId}/earn/{orderRef}/reversal")
    LoyaltyLedger.Reversed reverse(@PathVariable long customerId, @PathVariable String orderRef) {
        return ledger.reverse(customerId, orderRef.toUpperCase(Locale.ROOT));
    }

    @PostMapping("/loyalty/{customerId}/redeem")
    LoyaltyLedger.Redeemed redeem(@PathVariable long customerId, @Valid @RequestBody Redeem body) {
        return ledger.redeem(customerId, body.points());
    }
}
