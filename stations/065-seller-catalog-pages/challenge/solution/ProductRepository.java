package com.kartwala.sellerpages;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;

import java.util.Optional;

interface ProductRepository extends Repository<Product, Long> {

    /** A Page: the rows of this page, plus a count query for totalElements and totalPages. */
    Page<ProductCard> findBySellerId(long sellerId, Pageable pageable);

    /** Challenge 1: the same rows as a Slice: one row more than the page, and no count. */
    Slice<ProductCard> findSliceBySellerId(long sellerId, Pageable pageable);

    Optional<ProductCard> findByIdAndSellerId(long id, long sellerId);

    /** Challenge 2: how many rows come before this one in (price, id) order. */
    @Query("select count(p) from Product p where p.sellerId = :seller and (p.pricePaise < :price or (p.pricePaise = :price and p.id < :id))")
    long countBeforeAscending(long seller, int price, long id);

    @Query("select count(p) from Product p where p.sellerId = :seller and (p.pricePaise > :price or (p.pricePaise = :price and p.id < :id))")
    long countBeforeDescending(long seller, int price, long id);
}
