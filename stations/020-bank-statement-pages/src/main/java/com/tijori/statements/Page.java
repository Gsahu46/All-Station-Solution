package com.tijori.statements;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * One page of any list, as a generic record: Page&lt;Transaction&gt; here, Page&lt;Anything&gt; elsewhere.
 * T is bounded by Identified, so a page can name its last item's id: where a cursor would continue.
 */
record Page<T extends Page.Identified>(List<T> items, int page, int size, long totalItems, int totalPages, boolean hasNext) {

    interface Identified {
        long id();
    }

    /** Slices an already sorted list. The offset is a long: page x size can pass int's limit. */
    static <T extends Identified> Page<T> of(List<T> sorted, int page, int size) {
        long offset = (long) page * size;
        int from = (int) Math.min(offset, sorted.size());
        int to = (int) Math.min(offset + size, sorted.size());
        int totalPages = (sorted.size() + size - 1) / size;
        return new Page<>(List.copyOf(sorted.subList(from, to)), page, size, sorted.size(), totalPages, to < sorted.size());
    }

    /** The id of the last item on this page, or null if it is empty. */
    @JsonProperty("lastId")
    Long lastId() {
        return items.isEmpty() ? null : items.getLast().id();
    }
}
