package com.kartwala.recent;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * A LinkedHashMap in access order that drops its least recently used entry when it grows past maxSize.
 * accessOrder = true: every get or put moves the entry to the end, so the first entry is always the one
 * untouched the longest, and removeEldestEntry removes exactly that one.
 *
 * Not thread-safe, and in access order even get() changes the map. Callers must lock around every call.
 */
class LruMap<K, V> extends LinkedHashMap<K, V> {

    private final int maxSize;

    LruMap(int maxSize) {
        super(16, 0.75f, true);
        this.maxSize = maxSize;
    }

    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() > maxSize;
    }
}
