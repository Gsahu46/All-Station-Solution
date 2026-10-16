package com.kartwala.sellerpages;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.repository.Repository;

interface ProductRepository extends Repository<Product, Long> {

    /** A Page: the rows of this page, plus a count query for totalElements and totalPages. */
    Page<ProductCard> findBySellerId(long sellerId, Pageable pageable);
}
