package com.tijori.wallets;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
class TopUpController {

    /** Demo rules: at least ₹1, at most ₹1,00,000 in one top-up. */
    record Request(@Min(100) @Max(10_000_000) long amountPaise) {
    }

    private final TopUps topUps;

    TopUpController(TopUps topUps) {
        this.topUps = topUps;
    }

    /** Records a top-up and raises the balance. Nothing is charged here: the money's source is another system. */
    @PostMapping("/wallets/{id}/top-ups")
    @ResponseStatus(HttpStatus.CREATED)
    TopUps.TopUp topUp(@PathVariable long id, @Valid @RequestBody Request body) {
        return topUps.topUp(id, body.amountPaise());
    }

    @GetMapping("/wallets/{id}/limits")
    TopUps.Limits limits(@PathVariable long id) {
        return topUps.limits(id);
    }

    /** For a top-up whose money never arrived. Safe to repeat. */
    @PostMapping("/wallets/{id}/top-ups/{topUpId}/reversal")
    TopUps.Reversal reverse(@PathVariable long id, @PathVariable long topUpId) {
        return topUps.reverse(id, topUpId);
    }
}
