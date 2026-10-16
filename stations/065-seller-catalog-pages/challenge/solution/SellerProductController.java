package com.kartwala.sellerpages;

import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
import org.springframework.data.web.PageableDefault;
import org.springframework.data.web.PagedModel;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
class SellerProductController {

    private final SellerCatalog catalog;

    SellerProductController(SellerCatalog catalog) {
        this.catalog = catalog;
    }

    /**
     * ?page=0&size=20&sort=pricePaise,desc. Demo: the seller comes from a header; a real app takes it from the login.
     * Spring Data builds the Pageable from the query string and caps size at 100. @PageableDefault has its own size
     * (10) that wins over spring.data.web.pageable.default-page-size, so it is spelled out here.
     */
    @GetMapping("/seller/products")
    PagedModel<ProductCard> products(@RequestHeader("X-Seller-Id") long sellerId, @PageableDefault(size = 20, sort = "name") Pageable pageable) {
        return new PagedModel<>(catalog.page(sellerId, pageable));
    }

    record Feed(List<ProductCard> content, int number, int size, boolean hasNext) {
    }

    /** Challenge 1. */
    @GetMapping("/seller/products/feed")
    Feed feed(@RequestHeader("X-Seller-Id") long sellerId, @PageableDefault(size = 20, sort = "name") Pageable pageable) {
        Slice<ProductCard> slice = catalog.slice(sellerId, pageable);
        return new Feed(slice.getContent(), slice.getNumber(), slice.getSize(), slice.hasNext());
    }

    record Position(long productId, int page) {
    }

    /** Challenge 2. */
    @GetMapping("/seller/products/{id}/page")
    Position pageOf(@RequestHeader("X-Seller-Id") long sellerId, @PathVariable long id, @PageableDefault(size = 20, sort = "pricePaise") Pageable pageable) {
        return new Position(id, catalog.pageOf(sellerId, id, pageable));
    }
}
