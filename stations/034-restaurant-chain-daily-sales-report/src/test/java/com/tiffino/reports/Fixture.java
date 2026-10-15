package com.tiffino.reports;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;

/**
 * A small day the totals of which can be checked by hand: 14 October 2026 in India.
 * TF-01: 261.45 + 157.40 (9 a.m.) + 524.95 (1 p.m.) = 943.80. TF-02: 188.95 + 104.95 (noon) = 293.90.
 * TF-03: 92.45 (00:05) + 366.45 (8 p.m.) = 458.90. Two sales just outside the day, one on each side.
 */
final class Fixture {

    static final LocalDate DAY = LocalDate.of(2026, 10, 14);
    /** 11:30 in India on 15 October: the 14th is over. */
    static final Clock CLOCK = Clock.fixed(Instant.parse("2026-10-15T06:00:00Z"), DailySalesReport.INDIA);

    static Sale sale(String outlet, LocalDate day, String time, String rupees) {
        return new Sale(outlet, day.atTime(LocalTime.parse(time)).atZone(DailySalesReport.INDIA).toInstant(), new BigDecimal(rupees));
    }

    static final List<Sale> SALES = List.of(
            sale("TF-03", DAY.minusDays(1), "23:59", "500.00"),   // the 13th in India: not in the report
            sale("TF-03", DAY, "00:05", "92.45"),                 // still the 13th in UTC, already the 14th in India
            sale("TF-01", DAY, "09:15", "261.45"),
            sale("TF-01", DAY, "09:40", "157.40"),
            sale("TF-02", DAY, "12:10", "188.95"),
            sale("TF-02", DAY, "12:50", "104.95"),
            sale("TF-01", DAY, "13:05", "524.95"),
            sale("TF-03", DAY, "20:30", "366.45"),
            sale("TF-02", DAY.plusDays(1), "00:10", "700.00"));   // the 15th in India, though the 14th in UTC

    static final SalesFeed FEED = (from, to) -> SALES.stream().filter(s -> !s.at().isBefore(from) && s.at().isBefore(to)).toList();

    private Fixture() {
    }
}
