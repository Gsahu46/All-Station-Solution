package com.paysetu.cards;

import jakarta.validation.Valid;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.YearMonth;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@RestController
class CardController {

    /** Spaces between groups of digits are allowed, as people type them. */
    record SaveCardRequest(@NotNull @Pattern(regexp = "[0-9]{4}( ?[0-9]{2,4}){2,4}") String cardNumber,
                           @Min(1) @Max(12) int expiryMonth, @Min(2000) @Max(2100) int expiryYear,
                           @AssertTrue(message = "the customer must agree to save the card") boolean consent) {
    }

    record PaymentRequest(@NotNull @Pattern(regexp = "[A-Za-z0-9-]{3,40}") String orderId, @Min(1) long savedCardId,
                          @Min(100) @Max(10_000_000) long amountPaise) {
    }

    private static final Map<String, HttpStatus> STATUS = Map.of("succeeded", HttpStatus.CREATED, "declined", HttpStatus.PAYMENT_REQUIRED,
            "pending", HttpStatus.ACCEPTED, "failed", HttpStatus.UNPROCESSABLE_CONTENT);

    private static final Logger log = LoggerFactory.getLogger(CardController.class);

    private final Cards cards;
    private final Customers customers;

    CardController(Cards cards, Customers customers) {
        this.cards = cards;
        this.customers = customers;
    }

    @PostMapping("/customers/{id}/saved-cards")
    @ResponseStatus(HttpStatus.CREATED)
    Cards.SavedCard save(@PathVariable long id, @Valid @RequestBody SaveCardRequest body, Authentication who) {
        own(id, who);
        log.info("Saving a card for customer {}: {}", id, body);   // support needs this to debug failed saves
        return cards.save(id, body.cardNumber().replace(" ", ""), YearMonth.of(body.expiryYear(), body.expiryMonth()));
    }

    @GetMapping("/customers/{id}/saved-cards")
    List<Cards.SavedCard> list(@PathVariable long id, Authentication who) {
        return cards.list(id);   // read-only, and it shows only the last 4 digits
    }

    /** Pays as the signed-in customer, with one of their saved cards. Safe to repeat with the same order id. */
    @PostMapping("/payments")
    ResponseEntity<Cards.Payment> pay(@Valid @RequestBody PaymentRequest body, Authentication who) {
        Cards.Payment p = cards.pay(customers.idOf(who), body.savedCardId(), body.orderId().toUpperCase(Locale.ROOT), body.amountPaise());
        return ResponseEntity.status(STATUS.get(p.status())).body(p);
    }

    /** A customer's own cards only: someone else's customer id is refused (403) before anything is read. */
    private void own(long customerId, Authentication who) {
        if (customers.idOf(who) != customerId) {
            throw new AccessDeniedException("not this customer's cards");
        }
    }
}
