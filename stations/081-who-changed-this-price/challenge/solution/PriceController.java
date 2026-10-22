package com.kartwala.prices;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
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
    List<Prices.Entry> history(Authentication who, @PathVariable long id,
                               @RequestParam(defaultValue = "1970-01-01T00:00:00Z") Instant from, @RequestParam(defaultValue = "9999-01-01T00:00:00Z") Instant to) {
        if (!from.isBefore(to)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "from must be before to");
        }
        return prices.history(who, id, from, to);
    }

    @GetMapping("/products/{id}/price-at")
    Prices.PriceAt priceAt(Authentication who, @PathVariable long id, @RequestParam Instant time) {
        return prices.priceAt(who, id, time);
    }
}
