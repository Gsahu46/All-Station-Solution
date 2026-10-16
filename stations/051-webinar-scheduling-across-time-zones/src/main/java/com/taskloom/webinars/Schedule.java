package com.taskloom.webinars;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;

import java.time.Clock;
import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.temporal.TemporalAdjusters;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Turns the host's wall-clock time into instants (UTC) when a webinar is created, and instants back into anyone's
 * wall-clock time when it is read. Every session of a series is resolved on its own date, in the host's zone.
 */
@Service
class Schedule {

    enum Repeat { NONE, MONTHLY, MONTHLY_LAST_WEEKDAY }

    /** What is kept: the host's zone and the instants. No LocalDateTime is stored, because it means nothing alone. */
    record Webinar(long id, String title, ZoneId hostZone, int durationMinutes, List<Instant> sessions) {
    }

    record Session(Instant startsAt, OffsetDateTime hostTime, OffsetDateTime viewerTime) {
    }

    record WebinarView(long id, String title, String hostZone, String viewerZone, int durationMinutes, List<Session> sessions) {
    }

    private final Clock clock;
    private final Map<Long, Webinar> webinars = new ConcurrentHashMap<>();   // shortcut: in memory, lost on restart; a real app uses a table
    private final AtomicLong ids = new AtomicLong();

    Schedule(Clock clock) {
        this.clock = clock;
    }

    WebinarView create(String title, LocalDateTime startsAt, ZoneId zone, ZoneOffset offset, int durationMinutes, Repeat repeat, int count) {
        if (repeat == Repeat.NONE && count != 1) {
            throw unprocessable("A one-off webinar has 1 session; use repeat MONTHLY or MONTHLY_LAST_WEEKDAY for " + count + ".");
        }
        DayOfWeek weekday = startsAt.getDayOfWeek();
        if (repeat == Repeat.MONTHLY_LAST_WEEKDAY && !startsAt.toLocalDate().equals(startsAt.toLocalDate().with(TemporalAdjusters.lastInMonth(weekday)))) {
            throw unprocessable(startsAt.toLocalDate() + " is not the last " + weekday + " of its month.");
        }
        List<Instant> sessions = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            LocalDateTime local = switch (repeat) {
                // Always from the first date: Jan 31 + 1 month = Feb 28 (or 29), + 2 months = Mar 31. Chaining would stick at 28.
                case NONE, MONTHLY -> startsAt.plusMonths(i);
                case MONTHLY_LAST_WEEKDAY -> startsAt.plusMonths(i).with(TemporalAdjusters.lastInMonth(weekday));
            };
            sessions.add(resolve(local, zone, i == 0 ? offset : null));
        }
        if (!sessions.getFirst().isAfter(clock.instant())) {
            throw unprocessable("The first session, " + startsAt + " in " + zone + ", has already started.");
        }
        Webinar webinar = new Webinar(ids.incrementAndGet(), title, zone, durationMinutes, List.copyOf(sessions));
        webinars.put(webinar.id(), webinar);
        return view(webinar, zone);
    }

    Optional<WebinarView> find(long id, ZoneId viewerZone) {
        return Optional.ofNullable(webinars.get(id)).map(w -> view(w, viewerZone == null ? w.hostZone() : viewerZone));
    }

    /**
     * A wall-clock time in a zone is not always one instant: in a daylight saving gap it is none (clocks jump past
     * it), in an overlap it is two (clocks repeat it). Both are refused unless the client names the offset it means.
     */
    static Instant resolve(LocalDateTime local, ZoneId zone, ZoneOffset offset) {
        List<ZoneOffset> valid = zone.getRules().getValidOffsets(local);
        if (valid.isEmpty()) {
            throw unprocessable(local + " does not exist in " + zone + ": the clocks skip it for daylight saving.");
        }
        if (offset != null) {
            if (!valid.contains(offset)) {
                throw unprocessable(local + " in " + zone + " is at " + valid.getFirst() + ", not " + offset + ".");
            }
            return local.atOffset(offset).toInstant();
        }
        if (valid.size() > 1) {
            throw unprocessable(local + " happens twice in " + zone + " (" + valid.get(0) + " and " + valid.get(1)
                    + ") as the clocks go back; send \"offset\" to choose.");
        }
        return local.atOffset(valid.getFirst()).toInstant();
    }

    private static WebinarView view(Webinar w, ZoneId viewer) {
        List<Session> sessions = w.sessions().stream()
                .map(s -> new Session(s, s.atZone(w.hostZone()).toOffsetDateTime(), s.atZone(viewer).toOffsetDateTime())).toList();
        return new WebinarView(w.id(), w.title(), w.hostZone().getId(), viewer.getId(), w.durationMinutes(), sessions);
    }

    static ErrorResponseException unprocessable(String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT, detail);
        p.setTitle("Not a schedulable time");
        return new ErrorResponseException(HttpStatus.UNPROCESSABLE_CONTENT, p, null);
    }
}
