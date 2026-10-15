package com.tiffino.orders;

import java.util.concurrent.atomic.AtomicLong;

/** The order numbers before the fix, kept only in tests: a counter in each app's memory. */
final class OldOrderNumbers {

    private final AtomicLong counter = new AtomicLong();   // starts at 0 every time the app starts

    String next() {
        return "#" + counter.incrementAndGet();
    }
}
