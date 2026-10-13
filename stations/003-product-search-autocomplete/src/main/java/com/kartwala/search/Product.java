package com.kartwala.search;

/** A product in the catalogue. popularity = orders in the last 30 days; higher is suggested first. */
public record Product(long id, String name, int popularity) {
}
