package com.kartwala.catalog;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

interface ProductRepository extends JpaRepository<Product, Long> {

    Optional<Product> findByIdAndSellerId(long id, long sellerId);

    List<Product> findBySellerIdAndArchivedAtIsNullOrderById(long sellerId);

    List<Product> findBySellerIdOrderById(long sellerId);
}
