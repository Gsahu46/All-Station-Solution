package com.ghoomo.hotels;

import jakarta.persistence.criteria.Join;
import jakarta.persistence.criteria.Root;
import jakarta.persistence.criteria.Subquery;
import org.springframework.data.jpa.domain.Specification;

import java.util.Collection;

/** One small, testable Specification per filter. Each value becomes a bound parameter in the SQL. */
final class HotelSpecs {

    private HotelSpecs() {
    }

    static Specification<Hotel> inCity(String city) {
        return (root, query, cb) -> cb.equal(root.get("city"), city);
    }

    static Specification<Hotel> priceAtLeast(long paise) {
        return (root, query, cb) -> cb.greaterThanOrEqualTo(root.get("pricePerNightPaise"), paise);
    }

    static Specification<Hotel> priceAtMost(long paise) {
        return (root, query, cb) -> cb.lessThanOrEqualTo(root.get("pricePerNightPaise"), paise);
    }

    static Specification<Hotel> starsIn(Collection<Integer> stars) {
        return (root, query, cb) -> root.get("stars").in(stars.stream().map(Integer::shortValue).toList());
    }

    /** "Has this amenity", as EXISTS: one row per hotel, however many amenities it has. */
    static Specification<Hotel> hasAmenity(String code) {
        return (root, query, cb) -> {
            Subquery<Long> sub = query.subquery(Long.class);
            Root<Hotel> other = sub.from(Hotel.class);
            Join<Hotel, Amenity> amenity = other.join("amenities");
            sub.select(other.get("id")).where(cb.equal(other.get("id"), root.get("id")), cb.equal(amenity.get("code"), code));
            return cb.exists(sub);
        };
    }
}
