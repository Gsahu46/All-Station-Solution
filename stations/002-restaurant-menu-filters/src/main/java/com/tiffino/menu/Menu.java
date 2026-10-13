package com.tiffino.menu;

import java.util.List;

/** The response: which restaurant, and the dishes that matched, in the requested order. */
public record Menu(long restaurantId, String restaurantName, List<Dish> dishes) {
}
