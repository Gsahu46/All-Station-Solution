package com.ghoomo.hotels;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;

@RestController
class HotelController {

    private final HotelSearch search;

    HotelController(HotelSearch search) {
        this.search = search;
    }

    /** Prices are whole rupees in the query string (minPrice=3000), paise everywhere else. Demo limits on every value. */
    @GetMapping("/hotels")
    HotelSearch.Results hotels(@RequestParam(required = false) @Pattern(regexp = "[A-Za-z-]{3,30}") String city,
                               @RequestParam(required = false) @Min(0) @Max(100_000) Long minPrice,
                               @RequestParam(required = false) @Min(0) @Max(100_000) Long maxPrice,
                               @RequestParam(defaultValue = "") List<@Min(1) @Max(5) Integer> stars,
                               @RequestParam(defaultValue = "") @Size(max = 5) List<@Pattern(regexp = "[A-Za-z]{2,20}") String> amenities,
                               @RequestParam(defaultValue = "price") String sort,
                               @RequestParam(defaultValue = "0") @Min(0) @Max(100) int page,
                               @RequestParam(defaultValue = "20") @Min(1) @Max(50) int size,
                               @RequestParam(required = false) @Size(max = 50) String q) {
        if (minPrice != null && maxPrice != null && minPrice > maxPrice) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "minPrice is above maxPrice");
        }
        Set<String> codes = new TreeSet<>();
        amenities.forEach(a -> codes.add(a.toLowerCase(Locale.ROOT)));
        HotelSearch.Filters filters = new HotelSearch.Filters(city == null ? null : city.toLowerCase(Locale.ROOT),
                minPrice == null ? null : minPrice * 100, maxPrice == null ? null : maxPrice * 100, stars, codes, q);
        return search.search(filters, sort, page, size);
    }
}
