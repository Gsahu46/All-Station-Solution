package com.kartwala.checkout;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;

@RestController
class CheckoutController {

    record Line(@NotNull Long productId, @NotNull @Min(1) @Max(10) Integer quantity) {
    }

    /** Demo: the customer is named in the body. A real shop takes it from the login. */
    record NewCheckout(@NotNull Long customerId, @NotNull @Size(min = 1, max = 20) List<@Valid @NotNull Line> lines) {
    }

    private final CheckoutService checkouts;

    CheckoutController(CheckoutService checkouts) {
        this.checkouts = checkouts;
    }

    /** checkouts is the Spring proxy, not the object itself: calling through it is what starts the transaction. */
    @PostMapping("/checkouts")
    ResponseEntity<CheckoutService.CheckoutView> checkout(@Valid @RequestBody NewCheckout body) {
        CheckoutService.CheckoutView c = checkouts.checkout(body.customerId(),
                body.lines().stream().map(l -> new CheckoutService.LineRequest(l.productId(), l.quantity())).toList());
        return ResponseEntity.created(URI.create("/checkouts/" + c.id())).body(c);
    }

    @GetMapping("/checkouts/{id}")
    CheckoutService.CheckoutView get(@PathVariable long id) {
        return checkouts.find(id).orElseThrow(() -> CheckoutService.problem(HttpStatus.NOT_FOUND, "Checkout not found", "No checkout " + id + "."));
    }
}
