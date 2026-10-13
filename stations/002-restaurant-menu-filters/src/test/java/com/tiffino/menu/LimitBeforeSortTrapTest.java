package com.tiffino.menu;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.Comparator;
import java.util.List;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The customer taps "cheapest first" and the app asks for 5 dishes.
 */
@Import(LimitBeforeSortTrapTest.NaiveMenuController.class)
class LimitBeforeSortTrapTest extends ApiTest {

    /** The "before" code: takes the first 5 dishes as typed in by the kitchen, then sorts those 5. Kept only in tests. */
    @RestController
    static class NaiveMenuController {
        private final MenuCatalog catalog;

        NaiveMenuController(MenuCatalog catalog) {
            this.catalog = catalog;
        }

        @GetMapping("/naive/restaurants/{id}/cheapest5")
        List<Dish> cheapest5(@PathVariable long id) {
            return catalog.find(id).orElseThrow().dishes().stream()
                    .limit(5)
                    .sorted(Comparator.comparingInt(Dish::pricePaise))
                    .toList();
        }
    }

    @Test
    void limitBeforeSortReturnsFiveArbitraryDishesNeatlySorted() throws Exception {
        mvc.perform(get("/naive/restaurants/101/cheapest5"))
                .andExpect(status().isOk())
                // the bug: sorted, so it looks right, but these are just the first 5 rows; Rs 360 Mutton Rogan Josh is "cheap"
                .andExpect(jsonPath("$[*].name", contains(
                        "Masala Dosa", "Veg Hakka Noodles", "Paneer Butter Masala", "Chicken Biryani", "Mutton Rogan Josh")));
    }

    @Test
    void sortBeforeLimitReturnsTheFiveCheapestDishes() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("sort", "price_asc").param("limit", "5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes[*].name", contains(
                        "Idli Sambar", "Gulab Jamun (2 pcs)", "Curd Rice", "Lemon Rice", "Masala Dosa")));
    }
}
