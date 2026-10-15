package com.kartwala.reviews;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.math.BigDecimal;
import java.math.RoundingMode;

/** The stored aggregate: one row per product, kept up to date by every new review. Reading it is one row. */
@Entity
@Table(name = "product_ratings")
public class ProductRating {

    @Id
    private Long productId;
    private int reviewCount;
    private long starTotal;

    protected ProductRating() {
    }

    public Long getProductId() {
        return productId;
    }

    public int getReviewCount() {
        return reviewCount;
    }

    public long getStarTotal() {
        return starTotal;
    }

    /** Rounded half up to one decimal; null while nobody has reviewed. */
    BigDecimal average() {
        return reviewCount == 0 ? null : BigDecimal.valueOf(starTotal).divide(BigDecimal.valueOf(reviewCount), 1, RoundingMode.HALF_UP);
    }
}
