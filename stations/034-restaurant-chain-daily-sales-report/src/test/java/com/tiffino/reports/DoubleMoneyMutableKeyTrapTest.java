package com.tiffino.reports;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: the old report's two bugs, on the fixture day. */
class DoubleMoneyMutableKeyTrapTest {

    static final List<Sale> DAY = Fixture.FEED.between(Fixture.DAY.atStartOfDay(DailySalesReport.INDIA).toInstant(),
            Fixture.DAY.plusDays(1).atStartOfDay(DailySalesReport.INDIA).toInstant());

    @Test
    void summingInDoubleLosesAPaisa() {
        assertThat((188.95 + 104.95) * 100).isEqualTo(29_389.999999999996);   // and a cast to long cuts off the .999
        assertThat(OldDailyReport.outletTotalPaise(DAY, "TF-02")).isEqualTo(29_389);   // ₹293.89 for ₹293.90 of bills
    }

    @Test
    void aReusedMutableKeyLabelsEveryRowWithTheLastSale() {
        var old = OldDailyReport.byOutletHour(DAY);
        assertThat(old.size()).isGreaterThan(1);
        assertThat(old.keySet()).allSatisfy(k -> assertThat(k.outlet + " " + k.hour).isEqualTo("TF-03 20"));
    }

    @Test
    void theRealReportIsExactAndLabelledCorrectly() {
        var report = new DailySalesReport(Fixture.FEED, new Outlets(), Fixture.CLOCK).forDay(Fixture.DAY);
        assertThat(report.outlets()).extracting(DailySalesReport.OutletRow::outletId, DailySalesReport.OutletRow::totalPaise)
                .containsExactly(
                        org.assertj.core.groups.Tuple.tuple("TF-01", 94_380L),
                        org.assertj.core.groups.Tuple.tuple("TF-03", 45_890L),
                        org.assertj.core.groups.Tuple.tuple("TF-02", 29_390L));
    }
}
