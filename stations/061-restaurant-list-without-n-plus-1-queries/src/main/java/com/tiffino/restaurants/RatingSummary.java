package com.tiffino.restaurants;

/** A DTO projection: JPQL builds it straight from the aggregate, no Review entity is loaded. */
record RatingSummary(Long restaurantId, Double average, Long count) {
}
