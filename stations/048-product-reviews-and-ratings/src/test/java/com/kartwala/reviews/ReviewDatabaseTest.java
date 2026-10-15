package com.kartwala.reviews;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tables' rules with Java bypassed, a review rolled back with its totals, and posts racing each other. */
class ReviewDatabaseTest extends ApiTest {

    void insertReview(long product, long customer, long purchase, int stars) {
        jdbc.sql("INSERT INTO reviews (product_id, customer_id, purchase_id, stars, text, created_at) VALUES (?, ?, ?, ?, 'Direct', now())")
                .params(product, customer, purchase, stars).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        insertReview(1, 1, 1, 5);
        assertThatThrownBy(() -> insertReview(1, 1, 1, 4)).hasMessageContaining("reviews_one_per_customer");
        assertThatThrownBy(() -> insertReview(1, 2, 2, 6)).hasMessageContaining("reviews_stars_range");
        assertThatThrownBy(() -> insertReview(1, 4, 1, 5)).hasMessageContaining("reviews_purchase_fk");   // Asha's purchase, Imran's review
        assertThatThrownBy(() -> insertReview(2, 1, 1, 5)).hasMessageContaining("reviews_purchase_fk");   // a purchase of another product
        assertThatThrownBy(() -> jdbc.sql("UPDATE product_ratings SET review_count = 1, star_total = 6 WHERE product_id = 1").update())
                .hasMessageContaining("product_ratings_totals_consistent");
    }

    @Test
    void whenTheTotalsCannotBeUpdatedTheReviewIsNotSavedEither() throws Exception {
        jdbc.sql("DELETE FROM product_ratings WHERE product_id = 3").update();   // bedsheet: Asha has it delivered
        assertThatThrownBy(() -> review(3, 1, 4)).hasRootCauseInstanceOf(IllegalStateException.class);
        assertThat(jdbc.sql("SELECT count(*) FROM reviews").query(Long.class).single()).isZero();
    }

    @Test
    void twentyBuyersPostingAtOnceAreAllCounted() throws Exception {
        deliveredBuyers(20, 1);
        AtomicLong next = new AtomicLong(100);
        List<Integer> statuses = together(20, () -> {
            long customer = next.getAndIncrement();
            return review(1, customer, (int) (1 + customer % 5)).andReturn().getResponse().getStatus();
        });
        assertThat(statuses).containsOnly(201);
        assertThat(jdbc.sql("SELECT review_count || '/' || star_total FROM product_ratings WHERE product_id = 1").query(String.class).single())
                .isEqualTo(jdbc.sql("SELECT count(*) || '/' || sum(stars) FROM reviews WHERE product_id = 1").query(String.class).single())
                .isEqualTo("20/60");
    }

    @Test
    void oneCustomerPostingTenTimesAtOnceGetsOneReview() throws Exception {
        List<Integer> statuses = together(10, () -> review(1, 1, 5).andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(1);
        assertThat(statuses).filteredOn(s -> s == 409).hasSize(9);
        assertThat(jdbc.sql("SELECT review_count FROM product_ratings WHERE product_id = 1").query(Integer.class).single()).isEqualTo(1);
    }
}
