package com.ghoomo.hotels;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

interface HotelRepository extends JpaRepository<Hotel, Long>, JpaSpecificationExecutor<Hotel> {

    /** Every filter arrives as a Specification: criteria with bound parameters, never text glued into SQL. */
    @Override
    @EntityGraph(attributePaths = "amenities")
    Page<Hotel> findAll(Specification<Hotel> spec, Pageable pageable);
}
