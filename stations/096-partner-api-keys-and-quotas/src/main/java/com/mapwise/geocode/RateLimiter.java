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
 * One token bucket and one daily counter per partner, so one partner's bug only slows that partner.
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
        private double tokens;
        private Instant refilledAt;
        private LocalDate day;
        private int usedToday;

        Bucket(Partners.Partner plan, Instant now) {
            this.plan = plan;
            this.tokens = plan.burst();
            this.refilledAt = now;
            this.day = LocalDate.ofInstant(now, ZoneOffset.UTC);
        }

        /** synchronized: the check and the take are one step, or two requests could both take the last token. */
        synchronized Decision take(Instant now) {
            refill(now);
            if (usedToday >= plan.dailyQuota()) {
                Instant midnight = day.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant();
                return new Decision(false, seconds(Duration.between(now, midnight)),
                        "Daily quota of " + plan.dailyQuota() + " requests used. It resets at 00:00 UTC.");
            }
            if (tokens < 1) {
                double wait = (1 - tokens) / plan.perSecond();
                return new Decision(false, (long) Math.ceil(wait),
                        "Rate limit: " + plan.perSecond() + (plan.perSecond() == 1 ? " request" : " requests") + " a second, bursts of up to " + plan.burst() + ".");
            }
            tokens -= 1;
            usedToday++;   // only answered requests count against the day's quota
            return Decision.OK;
        }

        synchronized Usage usage(Instant now) {
            refill(now);
            return new Usage((long) tokens, usedToday, day.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant());
        }

        private void refill(Instant now) {
            if (now.isAfter(refilledAt)) {
                tokens = Math.min(plan.burst(), tokens + Duration.between(refilledAt, now).toNanos() / 1e9 * plan.perSecond());
                refilledAt = now;
            }
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
