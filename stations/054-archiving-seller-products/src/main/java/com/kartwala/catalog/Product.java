package com.kartwala.catalog;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

/**
 * A seller's product. It is never deleted while orders point at it: archiving sets archivedAt, and the row stays
 * for the order history. The timestamps are set by JPA callbacks, so no code path can forget them.
 */
@Entity
@Table(name = "products")
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private Long sellerId;
    private String name;
    private long pricePaise;
    private Instant archivedAt;
    private Instant createdAt;
    private Instant updatedAt;

    protected Product() {
    }

    Product(long sellerId, String name, long pricePaise) {
        this.sellerId = sellerId;
        this.name = name;
        this.pricePaise = pricePaise;
    }

    /** Before the INSERT: both stamps, equal. Micros, because that is what PostgreSQL keeps. */
    @PrePersist
    void stampCreated() {
        createdAt = now();
        updatedAt = createdAt;
    }

    /** Before every UPDATE Hibernate sends: only when something really changed (dirty checking decides). */
    @PreUpdate
    void stampUpdated() {
        updatedAt = now();
    }

    private static Instant now() {
        return Instant.now().truncatedTo(ChronoUnit.MICROS);
    }

    /** Archiving twice keeps the first date: the second DELETE changes nothing, so no UPDATE is sent. */
    void archive() {
        if (archivedAt == null) {
            archivedAt = now();
        }
    }

    public Long getId() {
        return id;
    }

    public Long getSellerId() {
        return sellerId;
    }

    public String getName() {
        return name;
    }

    public long getPricePaise() {
        return pricePaise;
    }

    public Instant getArchivedAt() {
        return archivedAt;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }
}
