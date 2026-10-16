package com.kartwala.sellerpages;

import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
import org.springframework.data.repository.Repository;

/** Test-only queries: the same rows as a Slice, and the old page query with whatever sort it is handed. */
interface OldProducts extends Repository<Product, Long> {

    /** A Slice: the rows plus one extra to know whether a next page exists. No count query. */
    Slice<ProductCard> findSliceBySellerId(long sellerId, Pageable pageable);
}
