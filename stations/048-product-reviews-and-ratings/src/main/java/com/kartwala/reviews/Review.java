package com.kartwala.reviews;

import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

@Entity
@Table(name = "reviews")
public class Review {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "product_id")
    private Product product;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "customer_id")
    private Customer customer;
    private Long purchaseId;
    private int stars;
    private String text;
    private Instant createdAt;

    protected Review() {
    }

    Review(Product product, Customer customer, long purchaseId, int stars, String text) {
        this.product = product;
        this.customer = customer;
        this.purchaseId = purchaseId;
        this.stars = stars;
        this.text = text;
        this.createdAt = Instant.now().truncatedTo(ChronoUnit.MICROS);   // what PostgreSQL keeps, so POST and GET agree
    }

    public Long getId() {
        return id;
    }

    public Customer getCustomer() {
        return customer;
    }

    public int getStars() {
        return stars;
    }

    public String getText() {
        return text;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
