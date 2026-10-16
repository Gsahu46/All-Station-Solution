package com.taskloom.webinars;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.stream.IntStream;

/** The scheduling code as it shipped, kept only in tests. */
class OldWebinarStore {

    /** Stored a LocalDateTime: 10:00, with no idea where. Every viewer got the same 10:00. */
    record OldWebinar(String title, LocalDateTime startsAt) {
        LocalDateTime showTo(String viewerZone) {
            return startsAt;   // nothing to convert from: the zone was never kept
        }
    }

    /** The later version stored an Instant, but repeated it by adding months in UTC, not in the host's zone. */
    static List<Instant> monthlyInUtc(Instant first, int count) {
        return IntStream.range(0, count).mapToObj(i -> first.atZone(ZoneOffset.UTC).plusMonths(i).toInstant()).toList();
    }
}
