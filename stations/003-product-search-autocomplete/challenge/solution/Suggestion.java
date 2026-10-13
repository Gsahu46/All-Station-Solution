package com.kartwala.search;

import java.util.List;

public record Suggestion(String prefix, List<Item> suggestions) {

    public record Item(long productId, String name, boolean inStock) {
    }
}
