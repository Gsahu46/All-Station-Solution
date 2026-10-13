package com.kartwala.search;

import org.springframework.stereotype.Component;

import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.NavigableMap;
import java.util.TreeMap;

/**
 * A sorted map from "text starting at a word" to product, built once at start-up.
 * "Samsung Galaxy M35 5G" is stored under "samsung galaxy m35 5g", "galaxy m35 5g", "m35 5g" and "5g",
 * so "sam" and "gal" both find it. Because the map is sorted, every key that starts with "sam" sits in one
 * contiguous range: from "sam" up to (not including) "sam" + the highest character. subMap reads only that range.
 */
@Component
class SuggestionIndex {

    private static final char SEPARATOR = '\u0000'; // keeps keys unique when two products share a word; sorts before any letter
    private final TreeMap<String, Product> byWordStart = new TreeMap<>();

    SuggestionIndex() {
        this(ProductCatalog.PRODUCTS);
    }

    SuggestionIndex(List<Product> products) {
        for (Product p : products) {
            String name = normalise(p.name());
            for (int i = 0; i < name.length(); i++) {
                if (i == 0 || name.charAt(i - 1) == ' ') {
                    byWordStart.put(name.substring(i) + SEPARATOR + p.id(), p);
                }
            }
        }
    }

    /**
     * Challenge 1: anything that is not a letter or digit counts as a space, so "Parle-G" and "parle g" are equal.
     * Then lower case with a fixed locale, trimmed, inner spaces collapsed. Used for names and prefixes alike.
     */
    static String normalise(String text) {
        return text.replaceAll("[^\\p{L}\\p{N}]+", " ").strip().toLowerCase(Locale.ROOT);
    }

    /** Every entry whose key starts with the prefix: a view of one slice of the map, no scan of the rest. */
    NavigableMap<String, Product> candidates(String normalisedPrefix) {
        return byWordStart.subMap(normalisedPrefix, true, normalisedPrefix + Character.MAX_VALUE, false);
    }

    List<Product> suggest(String normalisedPrefix, int limit) {
        return suggest(normalisedPrefix, limit, true);
    }

    /** Top N distinct products for the prefix, most popular first, ties by name. Challenge 2: the stock filter runs before the limit. */
    List<Product> suggest(String normalisedPrefix, int limit, boolean includeOutOfStock) {
        return candidates(normalisedPrefix).values().stream()
                .distinct()                                   // "sam" can match two words of the same product
                .filter(p -> includeOutOfStock || p.inStock())
                .sorted(Comparator.comparingInt(Product::popularity).reversed().thenComparing(Product::name))
                .limit(limit)
                .toList();
    }
}
