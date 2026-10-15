package com.chhotu.links;

import jakarta.annotation.PreDestroy;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.LongAdder;

/**
 * Counts clicks without slowing redirects: a click is one increment in memory, and a scheduled flush writes the
 * totals with one UPDATE per link. A redirect never waits for a row lock, even when a campaign link gets thousands of
 * clicks a second. The limit, by design: clicks not yet flushed (at most flush-ms worth) are lost if the process dies
 * without a clean shutdown; a clean shutdown flushes first.
 */
@Component
class ClickCounter {

    private final Map<String, LongAdder> pending = new ConcurrentHashMap<>();
    private final LinkStore links;

    ClickCounter(LinkStore links) {
        this.links = links;
    }

    void record(String code) {
        pending.computeIfAbsent(code, c -> new LongAdder()).increment();
    }

    long pending(String code) {
        LongAdder clicks = pending.get(code);
        return clicks == null ? 0 : clicks.sum();
    }

    /** sumThenReset takes each cell with an atomic get-and-set, so a click arriving during the flush is kept for the next one. */
    @Scheduled(fixedDelayString = "${chhotu.clicks.flush-ms}")
    @PreDestroy
    void flush() {
        pending.forEach((code, clicks) -> {
            long n = clicks.sumThenReset();
            if (n > 0) {
                links.addClicks(code, n);
            }
        });
    }
}
