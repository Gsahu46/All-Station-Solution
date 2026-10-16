package com.kartwala.sellerpages;

import java.time.LocalDate;

/** What a catalog row shows. Spring Data builds it straight from the query (a DTO projection), no entity loaded. */
record ProductCard(Long id, String name, int pricePaise, LocalDate createdOn) {
}
