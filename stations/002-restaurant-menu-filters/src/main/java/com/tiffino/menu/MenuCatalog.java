package com.tiffino.menu;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Restaurants and their dishes, in the order the kitchen typed them in (not sorted by anything).
 * In-memory for this station; a database comes in later stations.
 */
@Component
class MenuCatalog {

    private final Map<Long, Restaurant> restaurants = Map.of(
            101L, new Restaurant(101, "Annapoorna Mess", List.of(
                    new Dish(1, "Paneer Butter Masala", true, 24000, 410),
                    new Dish(2, "Chicken Biryani", false, 28000, 980),
                    new Dish(3, "Masala Dosa", true, 9000, 760),
                    new Dish(4, "Mutton Rogan Josh", false, 36000, 150),
                    new Dish(5, "Veg Hakka Noodles", true, 16000, 300),
                    new Dish(6, "Egg Curry", false, 15000, 220),
                    new Dish(7, "Idli Sambar", true, 6000, 640),
                    new Dish(8, "Dal Khichdi", true, 12000, 180),
                    new Dish(9, "Fish Fry", false, 26000, 90),
                    new Dish(10, "Curd Rice", true, 8000, 260),
                    new Dish(11, "Chole Bhature", true, 14000, 520),
                    new Dish(12, "Gulab Jamun (2 pcs)", true, 7000, 330),
                    new Dish(13, "Veg Thali", true, 19900, 450),
                    new Dish(14, "Lemon Rice", true, 8000, 120))),
            102L, new Restaurant(102, "Coastal Grill", List.of(
                    new Dish(21, "Prawn Ghee Roast", false, 42000, 210),
                    new Dish(22, "Chicken Sukka", false, 31000, 340),
                    new Dish(23, "Fish Thali", false, 29000, 280))));

    Optional<Restaurant> find(long id) {
        return Optional.ofNullable(restaurants.get(id));
    }
}
