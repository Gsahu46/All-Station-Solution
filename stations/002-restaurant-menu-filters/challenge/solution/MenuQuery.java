package com.tiffino.menu;

import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.stream.Stream;

/** Challenge 1 adds q; challenge 2 adds countMatching. Filters live in one place so both always agree. */
record MenuQuery(Boolean veg, Integer maxPrice, String q, String sort, int limit) {

    /** The station's tests still build a query without q. */
    MenuQuery(Boolean veg, Integer maxPrice, String sort, int limit) {
        this(veg, maxPrice, null, sort, limit);
    }

    List<Dish> apply(List<Dish> dishes) {
        return matching(dishes).sorted(comparator()).limit(limit).toList();
    }

    long countMatching(List<Dish> dishes) {
        return matching(dishes).count();
    }

    private Stream<Dish> matching(List<Dish> dishes) {
        // Locale.ROOT: on a Turkish server, "IDLI".toLowerCase() would otherwise be "ıdlı" and match nothing.
        String needle = q == null || q.isBlank() ? null : q.strip().toLowerCase(Locale.ROOT);
        return dishes.stream()
                .filter(d -> veg == null || d.veg() == veg)
                .filter(d -> maxPrice == null || d.pricePaise() <= maxPrice * 100)
                .filter(d -> needle == null || d.name().toLowerCase(Locale.ROOT).contains(needle));
    }

    private Comparator<Dish> comparator() {
        Comparator<Dish> byPrice = Comparator.comparingInt(Dish::pricePaise);
        Comparator<Dish> main = switch (sort) {
            case "price_asc" -> byPrice;
            case "price_desc" -> byPrice.reversed();
            case "recommended" -> Comparator.comparingInt(Dish::ordersLastWeek).reversed();
            default -> throw new IllegalArgumentException("unknown sort " + sort);
        };
        return main.thenComparing(Dish::name);
    }
}
