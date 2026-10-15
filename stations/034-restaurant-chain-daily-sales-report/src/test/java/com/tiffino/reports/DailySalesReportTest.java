package com.tiffino.reports;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.groups.Tuple.tuple;

/** The report without Spring: the day's edges, the order of rows, ties. */
class DailySalesReportTest {

    static DailySalesReport report(SalesFeed feed) {
        return new DailySalesReport(feed, new Outlets(), Fixture.CLOCK);
    }

    @Test
    void theDayIsMidnightToMidnightInIndia() {
        var r = report(Fixture.FEED).forDay(Fixture.DAY);
        assertThat(r.bills()).isEqualTo(7);
        assertThat(r.chainTotalPaise()).isEqualTo(169_660);
        assertThat(r.hours()).extracting(DailySalesReport.HourRow::hour, DailySalesReport.HourRow::totalPaise, DailySalesReport.HourRow::bills)
                .containsExactly(tuple(0, 9_245L, 1L), tuple(9, 41_885L, 2L), tuple(12, 29_390L, 2L), tuple(13, 52_495L, 1L), tuple(20, 36_645L, 1L));
    }

    @Test
    void eachOutletHasNameBillsAndBusiestHour() {
        assertThat(report(Fixture.FEED).forDay(Fixture.DAY).outlets())
                .extracting(DailySalesReport.OutletRow::outletId, DailySalesReport.OutletRow::name, DailySalesReport.OutletRow::bills, DailySalesReport.OutletRow::busiestHour)
                .containsExactly(tuple("TF-01", "Tiffino Koramangala", 3L, 13), tuple("TF-03", "Tiffino HSR Layout", 2L, 20), tuple("TF-02", "Tiffino Indiranagar", 2L, 12));
    }

    @Test
    void equalTotalsAreOrderedByOutletIdAndEqualHoursByTheEarlierOne() {
        LocalDate day = Fixture.DAY;
        List<Sale> sales = List.of(
                Fixture.sale("TF-07", day, "18:00", "100.00"),
                Fixture.sale("TF-04", day, "19:00", "60.00"),
                Fixture.sale("TF-04", day, "11:00", "40.00"));
        var outlets = report((f, t) -> sales).forDay(day).outlets();
        assertThat(outlets).extracting(DailySalesReport.OutletRow::outletId).containsExactly("TF-04", "TF-07");
        List<Sale> tie = List.of(Fixture.sale("TF-04", day, "19:00", "50.00"), Fixture.sale("TF-04", day, "11:00", "50.00"));
        assertThat(report((f, t) -> tie).forDay(day).outlets().getFirst().busiestHour()).isEqualTo(11);
    }

    @Test
    void aFractionOfAPaisaIsAnErrorNotARounding() {
        List<Sale> bad = List.of(new Sale("TF-01", Fixture.sale("TF-01", Fixture.DAY, "10:00", "1").at(), new BigDecimal("10.005")));
        assertThatThrownBy(() -> report((f, t) -> bad).forDay(Fixture.DAY)).isInstanceOf(ArithmeticException.class);
    }
}
