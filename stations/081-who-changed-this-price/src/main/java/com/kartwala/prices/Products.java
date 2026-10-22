package com.kartwala.prices;

import org.springframework.data.jpa.repository.JpaRepository;

interface Products extends JpaRepository<Product, Long> {
}
