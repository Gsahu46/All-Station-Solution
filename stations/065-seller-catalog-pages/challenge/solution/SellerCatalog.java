package com.kartwala.sellerpages;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
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
        return products.findBySellerId(sellerId, stable(sellerId, requested));
    }

    /** Challenge 1: the same checks and order, as a Slice. */
    @Transactional(readOnly = true)
    Slice<ProductCard> slice(long sellerId, Pageable requested) {
        return products.findSliceBySellerId(sellerId, stable(sellerId, requested));
    }

    /** Challenge 2: rows before the product in the stable order, divided by the page size. Price sorts only. */
    @Transactional(readOnly = true)
    int pageOf(long sellerId, long productId, Pageable requested) {
        Sort.Order order = requested.getSort().getOrderFor("pricePaise");
        if (order == null || requested.getSort().stream().count() != 1) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Only sort=pricePaise or sort=pricePaise,desc");
        }
        ProductCard product = products.findByIdAndSellerId(productId, sellerId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No product " + productId));
        long before = order.isAscending() ? products.countBeforeAscending(sellerId, product.pricePaise(), productId)
                : products.countBeforeDescending(sellerId, product.pricePaise(), productId);
        return (int) (before / requested.getPageSize());
    }

    private Pageable stable(long sellerId, Pageable requested) {
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
        return PageRequest.of(requested.getPageNumber(), requested.getPageSize(), stable);
    }
}
