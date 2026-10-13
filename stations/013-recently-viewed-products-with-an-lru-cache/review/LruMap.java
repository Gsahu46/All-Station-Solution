package com.kartwala.recent;

import java.util.LinkedHashMap;
import java.util.Map;

/** A bounded map: once it holds maxSize entries, the oldest one is removed. */
class LruMap<K, V> extends LinkedHashMap<K, V> {

    private final int maxSize;

    LruMap(int maxSize) {
        super(16, 0.75f);
        this.maxSize = maxSize;
    }

    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() >= maxSize;
    }
}
