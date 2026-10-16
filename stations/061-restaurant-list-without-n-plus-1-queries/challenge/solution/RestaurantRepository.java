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

    /** Challenge 1: the same page, only restaurants serving the cuisine (matched in any case). */
    @Query("""
            select r.id from Restaurant r where r.cityCode = :city
            and exists (select 1 from Restaurant x join x.cuisines c where x = r and lower(c.name) = lower(:cuisine))
            order by r.name, r.id""")
    List<Long> findPageOfIdsServing(String city, String cuisine, Pageable page);

    /** Challenge 2: best average first; no reviews last; ties by name, then id, so pages never overlap. */
    @Query("""
            select r.id from Restaurant r left join Review v on v.restaurant = r where r.cityCode = :city
            group by r.id, r.name order by avg(v.rating) desc nulls last, r.name, r.id""")
    List<Long> findPageOfIdsByRating(String city, Pageable page);

    /** Query 2: those restaurants with their cuisines, in one join. */
    @EntityGraph(attributePaths = "cuisines")
    List<Restaurant> findByIdIn(Collection<Long> ids);
}
