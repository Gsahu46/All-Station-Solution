package com.tiffino.menu;

import java.util.List;

record Restaurant(long id, String name, List<Dish> dishes) {
}
