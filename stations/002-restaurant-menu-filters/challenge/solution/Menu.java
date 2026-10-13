package com.tiffino.menu;

import java.util.List;

/** Challenge 2: totalMatching is counted after the filters and before the limit. */
public record Menu(long restaurantId, String restaurantName, List<Dish> dishes, long totalMatching) {
}
