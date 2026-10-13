package com.kartwala.wishlist;

import java.util.Locale;
import java.util.regex.Pattern;

/**
 * A stock-keeping unit, the product's code. A record: equals and hashCode come from its one field, so two Skus
 * with the same value are equal and land in the same HashSet bucket. Immutable: once a Sku is a key in a set or
 * map, it can never change underneath it.
 *
 * The constructor normalises before anything can compare it: "ph-12", "PH-12" and " PH-12 " all become "PH-12".
 * Normalise first, compare second; the other order is how the wishlist got three phones.
 */
public record Sku(String value) {

    private static final Pattern SHAPE = Pattern.compile("[A-Z0-9][A-Z0-9-]{1,29}");

    public Sku {
        if (value == null) {
            throw new IllegalArgumentException("A SKU is required.");
        }
        value = value.strip().toUpperCase(Locale.ROOT); // Locale.ROOT: on a Turkish server "mi-11" must not become "Mİ-11"
        if (!SHAPE.matcher(value).matches()) {
            throw new IllegalArgumentException("A SKU is 2-30 letters, digits or hyphens, like PH-12.");
        }
    }

    @Override
    public String toString() {
        return value;
    }
}
