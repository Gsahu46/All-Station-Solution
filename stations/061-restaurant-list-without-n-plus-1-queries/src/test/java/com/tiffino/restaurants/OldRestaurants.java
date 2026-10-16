package com.tiffino.restaurants;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;

import java.util.List;

/** The old queries, kept in the tests only. */
interface OldRestaurants extends Repository<Restaurant, Long> {

    List<Restaurant> findByCityCodeOrderByNameAscIdAsc(String cityCode, Pageable page);

    /** The first fix someone tries: fetch the cuisines in the same query, and keep paging. JOIN FETCH is an inner join. */
    @Query("select r from Restaurant r join fetch r.cuisines where r.cityCode = :city order by r.name, r.id")
    List<Restaurant> findWithCuisines(String city, Pageable page);
}
