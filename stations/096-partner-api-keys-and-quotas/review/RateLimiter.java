package com.mapwise.geocode;

import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * One window counter and one daily counter per partner, so one partner's bug only slows that partner.
 * shortcut: in this server's memory, so with N servers each partner gets N times the limit; keep the counters in a
 * shared store (Valkey) when the API runs on more than one server.
 */
@Component
class RateLimiter {

    /** allowed, or refused with the whole seconds to wait (Retry-After) and why. */
    record Decision(boolean allowed, long retryAfterSeconds, String reason) {
        static final Decision OK = new Decision(true, 0, null);
    }

    /** What a partner has left, for the usage endpoint. */
    record Usage(long tokensLeft, int usedToday, Instant quotaResetsAt) {
    }

    private final Clock clock;
    private final Map<Long, Bucket> buckets = new ConcurrentHashMap<>();   // only known partners get one: bounded

    RateLimiter(Clock clock) {
        this.clock = clock;
    }

    Decision take(Partners.Partner partner) {
        return buckets.computeIfAbsent(partner.id(), id -> new Bucket(partner, clock.instant())).take(clock.instant());
    }

    Usage usage(Partners.Partner partner) {
        return buckets.computeIfAbsent(partner.id(), id -> new Bucket(partner, clock.instant())).usage(clock.instant());
    }

    private static final class Bucket {
        private final Partners.Partner plan;
        private long windowSecond;
        private int inWindow;
        private LocalDate day;
        private int usedToday;

        Bucket(Partners.Partner plan, Instant now) {
            this.plan = plan;
            this.day = LocalDate.ofInstant(now, ZoneOffset.UTC);
        }

        /** Simpler than a bucket: count the requests in each second, at most `burst` of them. */
        synchronized Decision take(Instant now) {
            newDay(now);
            usedToday++;
            if (usedToday > plan.dailyQuota()) {
                Instant midnight = day.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant();
                return new Decision(false, seconds(Duration.between(now, midnight)),
                        "Daily quota of " + plan.dailyQuota() + " requests used. It resets at 00:00 UTC.");
            }
            if (now.getEpochSecond() != windowSecond) {
                windowSecond = now.getEpochSecond();
                inWindow = 0;
            }
            if (inWindow >= plan.burst()) {
                return new Decision(false, 1,
                        "Rate limit: " + plan.perSecond() + (plan.perSecond() == 1 ? " request" : " requests") + " a second, bursts of up to " + plan.burst() + ".");
            }
            inWindow++;
            return Decision.OK;
        }

        synchronized Usage usage(Instant now) {
            newDay(now);
            return new Usage(now.getEpochSecond() == windowSecond ? plan.burst() - inWindow : plan.burst(), usedToday,
                    day.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant());
        }

        private void newDay(Instant now) {
            LocalDate today = LocalDate.ofInstant(now, ZoneOffset.UTC);
            if (!today.equals(day)) {
                day = today;
                usedToday = 0;
            }
        }

        private static long seconds(Duration d) {
            return Math.max(1, (d.toMillis() + 999) / 1000);
        }
    }
}
