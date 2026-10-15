package com.kartwala.refunds;

import java.time.LocalDate;

/** One order with one item (demo). deliveredOn is null until delivery. hygieneItem: innerwear and the like. */
record Order(String id, String item, Category category, long pricePaise, LocalDate deliveredOn, boolean hygieneItem) {
}
