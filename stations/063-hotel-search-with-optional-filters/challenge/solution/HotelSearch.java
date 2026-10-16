package com.ghoomo.hotels;

import jakarta.persistence.EntityManager;
import jakarta.persistence.Tuple;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.CriteriaQuery;
import jakarta.persistence.criteria.Root;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

@Service
class HotelSearch {

    /** Each filter is optional: null (or empty) means "not filtered". Prices in paise. */
    record Filters(String city, Long minPaise, Long maxPaise, List<Integer> stars, Set<String> amenities, String q) {
        Filters(String city, Long minPaise, Long maxPaise, List<Integer> stars, Set<String> amenities) {
            this(city, minPaise, maxPaise, stars, amenities, null);
        }
    }

    record Card(long id, String name, String city, int stars, long pricePerNightPaise, List<String> amenities) {
    }

    record Results(long total, int page, String sort, List<Card> hotels, Map<Integer, Long> starsFacet) {
    }

    /** The whitelist: the only sorts there are. The id last, so equal prices keep one order across pages. */
    static final Map<String, Sort> SORTS = Map.of(
            "price", Sort.by("pricePerNightPaise", "id"),
            "-price", Sort.by(Sort.Order.desc("pricePerNightPaise"), Sort.Order.asc("id")),
            "stars", Sort.by(Sort.Order.asc("stars"), Sort.Order.asc("pricePerNightPaise"), Sort.Order.asc("id")),
            "-stars", Sort.by(Sort.Order.desc("stars"), Sort.Order.asc("pricePerNightPaise"), Sort.Order.asc("id")),
            "name", Sort.by("name", "id"));

    private final HotelRepository hotels;
    private final AmenityRepository amenities;
    private final EntityManager entities;

    HotelSearch(HotelRepository hotels, AmenityRepository amenities, EntityManager entities) {
        this.hotels = hotels;
        this.amenities = amenities;
        this.entities = entities;
    }

    @Transactional(readOnly = true)
    Results search(Filters f, String sort, int page, int size) {
        Sort order = SORTS.get(sort);
        if (order == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Sort by one of " + new TreeSet<>(SORTS.keySet()));
        }
        Set<String> unknown = new TreeSet<>(f.amenities());
        amenities.findAllById(f.amenities()).forEach(a -> unknown.remove(a.getCode()));
        if (!unknown.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unknown amenities " + unknown);
        }
        List<Specification<Hotel>> specs = new ArrayList<>();
        if (f.city() != null) specs.add(HotelSpecs.inCity(f.city()));
        if (f.minPaise() != null) specs.add(HotelSpecs.priceAtLeast(f.minPaise()));
        if (f.maxPaise() != null) specs.add(HotelSpecs.priceAtMost(f.maxPaise()));
        if (f.q() != null && !f.q().isBlank()) specs.add(HotelSpecs.nameContains(f.q()));
        f.amenities().forEach(code -> specs.add(HotelSpecs.hasAmenity(code)));
        Map<Integer, Long> facet = starsFacet(Specification.allOf(specs));   // every filter except stars
        if (!f.stars().isEmpty()) specs.add(HotelSpecs.starsIn(f.stars()));

        Page<Hotel> found = hotels.findAll(Specification.allOf(specs), PageRequest.of(page, size, order));
        List<Card> cards = found.stream().map(h -> new Card(h.getId(), h.getName(), h.getCity(), h.getStars(), h.getPricePerNightPaise(),
                h.getAmenities().stream().map(Amenity::getCode).sorted().toList())).toList();
        return new Results(found.getTotalElements(), page, sort, cards, facet);
    }

    /** Challenge 2: the same Specification, used in a GROUP BY query built with the Criteria API. */
    private Map<Integer, Long> starsFacet(Specification<Hotel> spec) {
        CriteriaBuilder cb = entities.getCriteriaBuilder();
        CriteriaQuery<Tuple> query = cb.createTupleQuery();
        Root<Hotel> root = query.from(Hotel.class);
        query.multiselect(root.get("stars"), cb.count(root)).where(spec.toPredicate(root, query, cb)).groupBy(root.get("stars"));
        Map<Integer, Long> counts = new TreeMap<>();
        entities.createQuery(query).getResultList().forEach(t -> counts.put(((Short) t.get(0)).intValue(), (Long) t.get(1)));
        return counts;
    }
}
