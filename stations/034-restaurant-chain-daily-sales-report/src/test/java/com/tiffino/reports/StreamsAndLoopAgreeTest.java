package com.tiffino.reports;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The same per-outlet totals written as a plain loop over whole paise, checked against the streams version on each of
 * the 7 demo days. Two independent ways to the same numbers.
 */
class StreamsAndLoopAgreeTest {

    static final Outlets OUTLETS = new Outlets();
    static final DemoSalesFeed DEMO = new DemoSalesFeed(Fixture.CLOCK, OUTLETS);

    static Map<String, Long> loop(List<Sale> sales) {
        Map<String, Long> totals = new HashMap<>();
        for (Sale s : sales) {
            totals.merge(s.outletId(), s.amountRupees().movePointRight(2).longValueExact(), Long::sum);
        }
        return totals;
    }

    @ParameterizedTest
    @ValueSource(ints = {1, 2, 3, 4, 5, 6, 7})
    void bothWaysGiveTheSameTotals(int daysAgo) {
        LocalDate day = Fixture.DAY.plusDays(1).minusDays(daysAgo);
        var report = new DailySalesReport(DEMO, OUTLETS, Fixture.CLOCK).forDay(day);
        var sales = DEMO.between(day.atStartOfDay(DailySalesReport.INDIA).toInstant(), day.plusDays(1).atStartOfDay(DailySalesReport.INDIA).toInstant());
        Map<String, Long> streams = new HashMap<>();
        report.outlets().forEach(o -> streams.put(o.outletId(), o.totalPaise()));
        assertThat(streams).hasSize(40).isEqualTo(loop(sales));
        assertThat(report.chainTotalPaise()).isEqualTo(loop(sales).values().stream().mapToLong(Long::longValue).sum());
    }
}
