package com.kartwala.catalog;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** Demo: the seller is named in the X-Seller-Id header. A real marketplace takes it from the seller's login. */
@RestController
class SellerProductController {

    private final SellerCatalog catalog;

    SellerProductController(SellerCatalog catalog) {
        this.catalog = catalog;
    }

    @DeleteMapping("/seller/products/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void archive(@RequestHeader("X-Seller-Id") long sellerId, @PathVariable long id, @RequestParam(defaultValue = "false") boolean purge) {
        if (purge) {
            catalog.purge(sellerId, id);
        } else {
            catalog.archive(sellerId, id);
        }
    }

    @PostMapping("/seller/products/{id}/restore")
    SellerCatalog.ProductView restore(@RequestHeader("X-Seller-Id") long sellerId, @PathVariable long id) {
        return catalog.restore(sellerId, id);
    }

    @GetMapping("/seller/products")
    List<SellerCatalog.ProductView> list(@RequestHeader("X-Seller-Id") long sellerId, @RequestParam(defaultValue = "false") boolean includeArchived) {
        return catalog.list(sellerId, includeArchived);
    }
}
