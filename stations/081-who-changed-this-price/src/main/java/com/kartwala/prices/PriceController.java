package com.kartwala.prices;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
class PriceController {

    /** Only the price: who and when are not the client's to say. Demo rule: from ₹1 to ₹10,00,000. */
    record NewPrice(@Min(100) @Max(100_000_000) long pricePaise) {
    }

    record PriceView(long id, String name, long pricePaise) {
    }

    private final Prices prices;

    PriceController(Prices prices) {
        this.prices = prices;
    }

    @PutMapping("/products/{id}/price")
    PriceView change(Authentication who, @PathVariable long id, @Valid @RequestBody NewPrice body) {
        Product p = prices.changePrice(who, id, body.pricePaise());
        return new PriceView(p.id(), p.name(), p.pricePaise());
    }

    @GetMapping("/products/{id}/history")
    List<Prices.Entry> history(Authentication who, @PathVariable long id) {
        return prices.history(who, id);
    }
}
