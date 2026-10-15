package com.tiffino.reports;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import static java.util.stream.Collectors.groupingBy;
import static java.util.stream.Collectors.reducing;

/**
 * One day's sales, per outlet and per hour, in India's day (midnight to midnight IST). Amounts are summed as
 * BigDecimal, exactly, and turned into paise once, at the end. Keys are immutable (String, Integer, a record).
 */
@Service
class DailySalesReport {

    static final ZoneId INDIA = ZoneId.of("Asia/Kolkata");

    /** A running total: an immutable value, combined with plus. */
    record Totals(BigDecimal amount, long bills) {
        static final Totals ZERO = new Totals(BigDecimal.ZERO, 0);

        static Totals of(Sale s) {
            return new Totals(s.amountRupees(), 1);
        }

        Totals plus(Totals other) {
            return new Totals(amount.add(other.amount), bills + other.bills);
        }

        long paise() {
            return amount.movePointRight(2).longValueExact();   // throws if a till ever sends a fraction of a paisa
        }
    }

    /** A composite key: a record, so equals and hashCode come from fields that can never change. */
    record OutletHour(String outletId, int hour) {
    }

    record OutletRow(String outletId, String name, long totalPaise, long bills, int busiestHour) {
    }

    record HourRow(int hour, long totalPaise, long bills) {
    }

    record Report(LocalDate date, long chainTotalPaise, long bills, List<OutletRow> outlets, List<HourRow> hours) {
    }

    private final SalesFeed feed;
    private final Outlets outlets;
    private final Clock clock;

    DailySalesReport(SalesFeed feed, Outlets outlets, Clock clock) {
        this.feed = feed;
        this.outlets = outlets;
        this.clock = clock;
    }

    static LocalDate today(Clock clock) {
        return LocalDate.now(clock.withZone(INDIA));
    }

    Report forDay(LocalDate date) {
        if (!date.isBefore(today(clock))) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Day not over", date + " has not ended in India yet; reports are for past days.");
        }
        Instant from = date.atStartOfDay(INDIA).toInstant();
        Instant to = date.plusDays(1).atStartOfDay(INDIA).toInstant();
        List<Sale> sales = feed.between(from, to);
        if (sales.isEmpty()) {
            throw problem(HttpStatus.NOT_FOUND, "No sales", "No sales were recorded on " + date + ".");
        }

        Map<String, Totals> byOutlet = sales.stream()
                .collect(groupingBy(Sale::outletId, reducing(Totals.ZERO, Totals::of, Totals::plus)));
        Map<Integer, Totals> byHour = sales.stream()
                .collect(groupingBy(s -> s.at().atZone(INDIA).getHour(), TreeMap::new, reducing(Totals.ZERO, Totals::of, Totals::plus)));
        Map<OutletHour, Totals> byOutletHour = sales.stream()
                .collect(groupingBy(s -> new OutletHour(s.outletId(), s.at().atZone(INDIA).getHour()), reducing(Totals.ZERO, Totals::of, Totals::plus)));
        Totals chain = byOutlet.values().stream().reduce(Totals.ZERO, Totals::plus);

        List<OutletRow> outletRows = byOutlet.entrySet().stream()
                .sorted(Map.Entry.<String, Totals>comparingByValue(Comparator.comparing(Totals::amount)).reversed()
                        .thenComparing(Map.Entry.<String, Totals>comparingByKey()))   // highest first; equal totals by outlet id
                .map(e -> new OutletRow(e.getKey(), outlets.name(e.getKey()), e.getValue().paise(), e.getValue().bills(),
                        busiestHour(byOutletHour, e.getKey())))
                .toList();
        List<HourRow> hourRows = byHour.entrySet().stream()
                .map(e -> new HourRow(e.getKey(), e.getValue().paise(), e.getValue().bills()))
                .toList();
        return new Report(date, chain.paise(), chain.bills(), outletRows, hourRows);
    }

    /** Each outlet's total for the 7 India days ending on lastDay, highest first. */
    Map<String, Long> weekTotals(LocalDate lastDay) {
        if (!lastDay.isBefore(today(clock))) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Day not over", lastDay + " has not ended in India yet; reports are for past days.");
        }
        Instant from = lastDay.minusDays(6).atStartOfDay(INDIA).toInstant();
        Instant to = lastDay.plusDays(1).atStartOfDay(INDIA).toInstant();
        Map<String, Totals> byOutlet = feed.between(from, to).stream()
                .collect(groupingBy(Sale::outletId, reducing(Totals.ZERO, Totals::of, Totals::plus)));
        return byOutlet.entrySet().stream()
                .sorted(Map.Entry.<String, Totals>comparingByValue(Comparator.comparing(Totals::amount)).reversed()
                        .thenComparing(Map.Entry.<String, Totals>comparingByKey()))
                .collect(LinkedHashMap::new, (m, e) -> m.put(e.getKey(), e.getValue().paise()), Map::putAll);
    }

    /** For each city, the hour with the highest sales across its outlets; on a tie, the earlier hour. */
    Map<String, Integer> busiestHourByCity(LocalDate date) {
        Instant from = date.atStartOfDay(INDIA).toInstant();
        Instant to = date.plusDays(1).atStartOfDay(INDIA).toInstant();
        Map<String, Map<Integer, Totals>> byCityHour = feed.between(from, to).stream()
                .collect(groupingBy(s -> outlets.city(s.outletId()),
                        groupingBy(s -> s.at().atZone(INDIA).getHour(), reducing(Totals.ZERO, Totals::of, Totals::plus))));
        Map<String, Integer> peaks = new TreeMap<>();
        byCityHour.forEach((city, hours) -> peaks.put(city, hours.entrySet().stream()
                .max(Comparator.<Map.Entry<Integer, Totals>, BigDecimal>comparing(e -> e.getValue().amount()).thenComparing(e -> -e.getKey()))
                .orElseThrow().getKey()));
        return peaks;
    }

    /** The outlet's hour with the highest sales; on a tie, the earlier hour. */
    static int busiestHour(Map<OutletHour, Totals> byOutletHour, String outletId) {
        return byOutletHour.entrySet().stream()
                .filter(e -> e.getKey().outletId().equals(outletId))
                .max(Comparator.<Map.Entry<OutletHour, Totals>, BigDecimal>comparing(e -> e.getValue().amount())
                        .thenComparing(e -> -e.getKey().hour()))
                .orElseThrow()
                .getKey().hour();
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
