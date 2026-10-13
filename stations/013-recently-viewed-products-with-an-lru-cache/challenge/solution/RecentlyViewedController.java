package com.kartwala.recent;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/users/{userId}/recently-viewed")
class RecentlyViewedController {

    record View(@NotNull @Positive Long productId) {
    }

    record History(long userId, List<Long> productIds) {
    }

    private final RecentlyViewed recentlyViewed;

    RecentlyViewedController(RecentlyViewed recentlyViewed) {
        this.recentlyViewed = recentlyViewed;
    }

    /** Record a view and return the history. Viewing the same product again moves it to the front; it is never listed twice. */
    @PostMapping
    History view(@PathVariable @Positive long userId, @Valid @RequestBody View view) {
        return new History(userId, recentlyViewed.record(userId, view.productId()));
    }

    /** Challenge 1: 204 whether or not it was there. */
    @DeleteMapping("/{productId}")
    ResponseEntity<Void> remove(@PathVariable @Positive long userId, @PathVariable long productId) {
        recentlyViewed.remove(userId, productId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping
    History history(@PathVariable @Positive long userId) {
        return new History(userId, recentlyViewed.list(userId));
    }
}
