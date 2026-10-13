package com.tiffino.menu;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Plain unit tests for the stream pipeline: no Spring, so they run in milliseconds. */
class MenuQueryTest {

    private final List<Dish> dishes = List.of(
            new Dish(1, "Rava Idli", true, 9000, 50),
            new Dish(2, "Appam", true, 9000, 50),
            new Dish(3, "Kheema Pav", false, 12000, 70),
            new Dish(4, "Upma", true, 5000, 10));

    @Test
    void filterSortLimitInThatOrder() {
        var result = new MenuQuery(true, null, "price_asc", 2).apply(dishes);
        assertThat(result).extracting(Dish::name).containsExactly("Upma", "Appam");
    }

    @Test
    void recommendedTiesAreBrokenByName() {
        var result = new MenuQuery(null, null, "recommended", 10).apply(dishes);
        assertThat(result).extracting(Dish::name).containsExactly("Kheema Pav", "Appam", "Rava Idli", "Upma");
    }

    @Test
    void maxPriceComparesRupeesWithPaiseExactly() {
        assertThat(new MenuQuery(null, 90, "price_asc", 10).apply(dishes)).extracting(Dish::id).containsExactly(4, 2, 1);
        assertThat(new MenuQuery(null, 89, "price_asc", 10).apply(dishes)).extracting(Dish::id).containsExactly(4);
    }

    @Test
    void theInputListIsNotChanged() {
        new MenuQuery(null, null, "price_desc", 1).apply(dishes);
        assertThat(dishes).extracting(Dish::id).containsExactly(1, 2, 3, 4);
    }
}
