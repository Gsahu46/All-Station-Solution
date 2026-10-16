package com.kartwala.sellerpages;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.LocalDate;

@Entity
@Table(name = "products")
class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(name = "seller_id")
    private long sellerId;
    private String name;
    @Column(name = "price_paise")
    private int pricePaise;
    @Column(name = "created_on")
    private LocalDate createdOn;

    protected Product() {
    }
}
