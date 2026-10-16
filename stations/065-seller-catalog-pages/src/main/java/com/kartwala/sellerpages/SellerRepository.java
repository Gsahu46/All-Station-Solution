package com.kartwala.sellerpages;

import org.springframework.data.jpa.repository.JpaRepository;

interface SellerRepository extends JpaRepository<Seller, Long> {
}
