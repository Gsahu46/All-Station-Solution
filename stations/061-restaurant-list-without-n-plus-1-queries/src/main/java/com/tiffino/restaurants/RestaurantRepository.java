package com.tiffino.restaurants;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.Collection;
import java.util.List;

interface RestaurantRepository extends JpaRepository<Restaurant, Long> {

    /** Query 1: one page of ids. No collection is joined, so the database applies LIMIT and OFFSET. */
    @Query("select r.id from Restaurant r where r.cityCode = :city order by r.name, r.id")
    List<Long> findPageOfIds(String city, Pageable page);

    /** Query 2: those restaurants with their cuisines, in one join. */
    @EntityGraph(attributePaths = "cuisines")
    List<Restaurant> findByIdIn(Collection<Long> ids);
}
