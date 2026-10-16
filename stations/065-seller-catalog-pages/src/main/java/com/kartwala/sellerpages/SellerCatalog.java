package com.kartwala.sellerpages;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.Set;

@Service
class SellerCatalog {

    /** The columns a seller may sort by. Each has an index ending in id. */
    static final Set<String> SORTABLE = Set.of("name", "pricePaise", "createdOn");

    private final ProductRepository products;
    private final SellerRepository sellers;

    SellerCatalog(ProductRepository products, SellerRepository sellers) {
        this.products = products;
        this.sellers = sellers;
    }

    @Transactional(readOnly = true)
    Page<ProductCard> page(long sellerId, Pageable requested) {
        for (Sort.Order order : requested.getSort()) {
            if (!SORTABLE.contains(order.getProperty())) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Sort by one of " + new java.util.TreeSet<>(SORTABLE));
            }
        }
        if (!sellers.existsById(sellerId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No seller " + sellerId);
        }
        // The tie-breaker: with id last, every row has exactly one place, so no row repeats or vanishes between pages.
        Sort stable = requested.getSort().and(Sort.by("id"));
        return products.findBySellerId(sellerId, PageRequest.of(requested.getPageNumber(), requested.getPageSize(), stable));
    }
}
