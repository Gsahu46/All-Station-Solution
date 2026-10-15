package com.tiffino.reports;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: TF-01 to TF-20 are in Bengaluru, TF-21 to TF-40 in Pune. Add Outlets.city(outletId) and
 * DailySalesReport.busiestHourByCity(day): for each city, the hour with the highest sales across its outlets
 * (earlier hour on a tie). One stream, grouping by city and then by hour.
 */
class CityPeakHourChallengeTest {

    @Test
    void eachCityHasItsOwnPeak() {
        var day = Fixture.DAY;
        List<Sale> sales = List.of(
                Fixture.sale("TF-01", day, "13:10", "100.00"),
                Fixture.sale("TF-02", day, "13:40", "50.00"),
                Fixture.sale("TF-03", day, "20:00", "120.00"),
                Fixture.sale("TF-21", day, "20:15", "80.00"),
                Fixture.sale("TF-22", day, "09:05", "70.00"),
                Fixture.sale("TF-22", day, "10:30", "20.00"));
        var report = new DailySalesReport((from, to) -> sales, new Outlets(), Fixture.CLOCK);
        assertThat(report.busiestHourByCity(day)).isEqualTo(Map.of("Bengaluru", 13, "Pune", 20));
    }

    @Test
    void outletsKnowTheirCity() {
        Outlets outlets = new Outlets();
        assertThat(outlets.city("TF-20")).isEqualTo("Bengaluru");
        assertThat(outlets.city("TF-21")).isEqualTo("Pune");
    }
}
