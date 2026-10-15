package com.kartwala.flashsale;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.Locale;

@RestController
class PurchaseController {

    /** customerId stands in for the signed-in customer (demo); a real app takes it from the login. */
    record PurchaseRequest(@NotNull @Pattern(regexp = "(?i)C-\\d{6}", message = "must look like C-000123") String customerId) {
    }

    private final FlashSaleStore store;

    PurchaseController(FlashSaleStore store) {
        this.store = store;
    }

    /** Reserves one unit for the customer: a purchase record is created; no payment is taken in this station. */
    @PostMapping("/flash-sales/{saleId}/purchases")
    @ResponseStatus(HttpStatus.CREATED)
    FlashSaleStore.Purchase buy(@PathVariable long saleId, @Valid @RequestBody PurchaseRequest request) {
        String customer = request.customerId().toUpperCase(Locale.ROOT);
        try {
            return store.buy(saleId, customer).orElseThrow(() -> refusal(saleId));
        } catch (DuplicateKeyException e) {   // purchases_one_per_customer; the transaction put the phone back
            throw problem(HttpStatus.CONFLICT, "Already bought", "Customer " + customer + " already has one from this sale.");
        }
    }

    @GetMapping("/flash-sales/{saleId}")
    FlashSaleStore.Status sale(@PathVariable long saleId) {
        return store.status(saleId).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Sale not found", "No flash sale " + saleId + "."));
    }

    @DeleteMapping("/flash-sales/{saleId}/purchases/{purchaseId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void cancel(@PathVariable long saleId, @PathVariable long purchaseId) {
        if (!store.cancel(saleId, purchaseId)) {
            throw problem(HttpStatus.NOT_FOUND, "Purchase not found", "No purchase " + purchaseId + " in sale " + saleId + ".");
        }
    }

    /** No phone was taken: say why. */
    private ErrorResponseException refusal(long saleId) {
        FlashSaleStore.Sale sale = store.sale(saleId).orElse(null);
        if (sale == null) {
            return problem(HttpStatus.NOT_FOUND, "Sale not found", "No flash sale " + saleId + ".");
        }
        OffsetDateTime now = OffsetDateTime.now();
        if (now.isBefore(sale.startsAt())) {
            return problem(HttpStatus.CONFLICT, "Not started", "Sale " + saleId + " starts at " + sale.startsAt() + ".");
        }
        if (!now.isBefore(sale.endsAt())) {
            return problem(HttpStatus.CONFLICT, "Sale ended", "Sale " + saleId + " has ended.");
        }
        return problem(HttpStatus.CONFLICT, "Sold out", "Sale " + saleId + " is sold out.");
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
