package com.kartwala.search;

/** Challenge 2 adds inStock. The three-argument constructor keeps older code (and tests) working: in stock by default. */
public record Product(long id, String name, int popularity, boolean inStock) {

    public Product(long id, String name, int popularity) {
        this(id, name, popularity, true);
    }
}
