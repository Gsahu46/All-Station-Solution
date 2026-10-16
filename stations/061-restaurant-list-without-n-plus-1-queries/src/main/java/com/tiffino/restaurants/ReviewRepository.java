package com.tiffino.restaurants;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.Collection;
import java.util.List;

interface ReviewRepository extends JpaRepository<Review, Long> {

    /** Query 3: average and count for every restaurant on the page, grouped by the database. */
    @Query("""
            select new com.tiffino.restaurants.RatingSummary(r.restaurant.id, avg(r.rating), count(r))
            from Review r where r.restaurant.id in :ids group by r.restaurant.id""")
    List<RatingSummary> summariesFor(Collection<Long> ids);
}
