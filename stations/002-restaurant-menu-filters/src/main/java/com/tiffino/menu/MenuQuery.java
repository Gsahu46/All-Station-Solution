package com.tiffino.menu;

import java.util.Comparator;
import java.util.List;

/**
 * The customer's filters, already validated by the controller, and the one place that applies them.
 * Order matters: filter, then sort, then limit. Limiting first is this station's trap.
 *
 * @param veg      null = every dish, true = veg only, false = non-veg only
 * @param maxPrice in whole rupees, inclusive; null = no limit
 * @param sort     recommended (most ordered first), price_asc or price_desc
 * @param limit    how many dishes to return, at most
 */
record MenuQuery(Boolean veg, Integer maxPrice, String sort, int limit) {

    List<Dish> apply(List<Dish> dishes) {
        return dishes.stream()
                .filter(d -> veg == null || d.veg() == veg)
                .filter(d -> maxPrice == null || d.pricePaise() <= maxPrice * 100)
                .sorted(comparator())
                .limit(limit)
                .toList();
    }

    /** Ties are broken by name, so the same request always gives the same order. */
    private Comparator<Dish> comparator() {
        Comparator<Dish> byPrice = Comparator.comparingInt(Dish::pricePaise);
        Comparator<Dish> main = switch (sort) {
            case "price_asc" -> byPrice;
            case "price_desc" -> byPrice.reversed();
            case "recommended" -> Comparator.comparingInt(Dish::ordersLastWeek).reversed();
            default -> throw new IllegalArgumentException("unknown sort " + sort); // the controller only lets the three through
        };
        return main.thenComparing(Dish::name);
    }
}
