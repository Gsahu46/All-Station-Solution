package com.tiffino.menu;

/** One menu item. Prices are whole paise (24000 = Rs 240.00), never a double. */
public record Dish(int id, String name, boolean veg, int pricePaise, int ordersLastWeek) {
}
