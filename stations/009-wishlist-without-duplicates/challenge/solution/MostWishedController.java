package com.kartwala.wishlist;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Comparator;
import java.util.List;
import java.util.Map;

/** Challenge 2. Counting happens in a HashMap<Sku, Integer>; ranking sorts its entries. */
@RestController
class MostWishedController {

    record Wished(String sku, int wishlists) {
    }

    private final Wishlists wishlists;

    MostWishedController(Wishlists wishlists) {
        this.wishlists = wishlists;
    }

    @GetMapping("/products/most-wished")
    List<Wished> mostWished(@RequestParam(defaultValue = "10") @Min(1) @Max(50) int limit) {
        return wishlists.counts().entrySet().stream()
                .sorted(Map.Entry.<Sku, Integer>comparingByValue().reversed()
                        .thenComparing(e -> e.getKey().value()))
                .limit(limit)
                .map(e -> new Wished(e.getKey().value(), e.getValue()))
                .toList();
    }
}
