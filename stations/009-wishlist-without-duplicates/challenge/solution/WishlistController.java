package com.kartwala.wishlist;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/wishlists/{id}")
class WishlistController {

    record AddItem(@NotNull String sku) {
    }

    record Merge(@NotNull List<String> skus) {
    }

    record Item(String sku, String name, int pricePaise) {
    }

    record WishlistView(long wishlistId, int count, List<Item> items) {
    }

    private final Wishlists wishlists;
    private final Catalog catalog;

    WishlistController(Wishlists wishlists, Catalog catalog) {
        this.wishlists = wishlists;
        this.catalog = catalog;
    }

    @GetMapping
    WishlistView get(@PathVariable long id) {
        return view(id);
    }

    /** 201 if the product was added, 200 if it was already there. Either way it is in the list exactly once. */
    @PostMapping("/items")
    ResponseEntity<WishlistView> add(@PathVariable long id, @Valid @RequestBody AddItem request) {
        requireWishlist(id);
        Sku sku = sku(request.sku());
        if (catalog.find(sku).isEmpty()) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown product", "No product has this SKU.");
        }
        boolean added = wishlists.add(id, sku);
        return ResponseEntity.status(added ? HttpStatus.CREATED : HttpStatus.OK).body(view(id));
    }

    /** Challenge 1: check every SKU first, then add them all. One bad SKU and nothing is merged. */
    @PostMapping("/merge")
    WishlistView merge(@PathVariable long id, @Valid @RequestBody Merge request) {
        requireWishlist(id);
        List<Sku> skus = request.skus().stream().map(WishlistController::sku).toList();
        if (skus.stream().anyMatch(s -> catalog.find(s).isEmpty())) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown product", "At least one SKU is not in the catalogue.");
        }
        wishlists.addAll(id, skus);
        return view(id);
    }

    /** 204 whether or not it was in the list: removing twice is safe (station 008). */
    @DeleteMapping("/items/{sku}")
    ResponseEntity<Void> remove(@PathVariable long id, @PathVariable String sku) {
        requireWishlist(id);
        wishlists.remove(id, sku(sku));
        return ResponseEntity.noContent().build();
    }

    private WishlistView view(long id) {
        List<Item> items = wishlists.items(id).orElseThrow(WishlistController::notFound).stream()
                .map(sku -> catalog.find(sku).orElseThrow())
                .map(p -> new Item(p.sku().value(), p.name(), p.pricePaise()))
                .toList();
        return new WishlistView(id, items.size(), items);
    }

    private static Sku sku(String raw) {
        try {
            return new Sku(raw);
        } catch (IllegalArgumentException e) {
            throw problem(HttpStatus.BAD_REQUEST, "Invalid SKU", e.getMessage()); // our own fixed message, not the input
        }
    }

    private void requireWishlist(long id) {
        if (!wishlists.exists(id)) {
            throw notFound();
        }
    }

    private static ErrorResponseException notFound() {
        return problem(HttpStatus.NOT_FOUND, "Wishlist not found", "No wishlist has this id.");
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail body = ProblemDetail.forStatusAndDetail(status, detail);
        body.setTitle(title);
        return new ErrorResponseException(status, body, null);
    }
}
