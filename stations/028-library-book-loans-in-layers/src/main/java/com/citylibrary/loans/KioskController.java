package com.citylibrary.loans;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Locale;

/** The self-service kiosk: a card and a barcode instead of ids. The same service, so the same rules. */
@RestController
class KioskController {

    record Checkout(@NotBlank String cardNumber, @NotBlank String barcode) {
    }

    private final LoanService service;

    KioskController(LoanService service) {
        this.service = service;
    }

    @PostMapping("/kiosk/checkouts")
    @ResponseStatus(HttpStatus.CREATED)
    Model.Loan checkout(@Valid @RequestBody Checkout c) {
        return service.borrowAtKiosk(c.cardNumber().strip().toUpperCase(Locale.ROOT), c.barcode().strip().toUpperCase(Locale.ROOT));
    }
}
