package com.kartwala.search;

import java.util.List;

/** The response: the normalised prefix that was searched, and the suggestions, most popular first. */
public record Suggestion(String prefix, List<Item> suggestions) {

    public record Item(long productId, String name) {
    }
}
