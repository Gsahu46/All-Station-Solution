package com.citylibrary.loans;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** The web API: turns HTTP into service calls and back. No rules here. */
@RestController
class LoanController {

    record BorrowRequest(@NotBlank String memberId, @NotBlank String bookId) {
    }

    record FinePayment(@NotNull @Positive Long amountPaise) {
    }

    private final LoanService service;

    LoanController(LoanService service) {
        this.service = service;
    }

    @PostMapping("/loans")
    @ResponseStatus(HttpStatus.CREATED)
    Model.Loan borrow(@Valid @RequestBody BorrowRequest r) {
        return service.borrow(r.memberId(), r.bookId());
    }

    @PostMapping("/loans/{id}/return")
    Model.Loan giveBack(@PathVariable String id) {
        return service.giveBack(id);
    }

    /** Challenge 1. */
    @PostMapping("/members/{id}/fine-payments")
    Model.Member payFine(@PathVariable String id, @Valid @RequestBody FinePayment payment) {
        return service.payFine(id, payment.amountPaise());
    }

    /** Challenge 2. */
    @PostMapping("/loans/{id}/renewals")
    Model.Loan renew(@PathVariable String id) {
        return service.renew(id);
    }

    @GetMapping("/members/{id}/loans")
    List<Model.Loan> loansOf(@PathVariable String id) {
        return service.loansOf(id);
    }
}
