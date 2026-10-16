package com.kartwala.sellerpages;

import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.data.web.PagedModel;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

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
}
