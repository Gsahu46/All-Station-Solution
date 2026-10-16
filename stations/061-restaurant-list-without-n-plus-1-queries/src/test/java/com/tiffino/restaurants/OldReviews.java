package com.tiffino.restaurants;

import org.springframework.data.repository.Repository;

import java.util.List;

/** The old per-restaurant review query, kept in the tests only. */
interface OldReviews extends Repository<Review, Long> {

    List<Review> findByRestaurantId(Long restaurantId);
}
