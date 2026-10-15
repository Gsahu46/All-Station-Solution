package com.tiffino.reports;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Challenge 1: owners want a week at a glance. Add DailySalesReport.weekTotals(lastDay): each outlet's total in paise
 * for the 7 India days ending on lastDay, highest first (a LinkedHashMap keeps that order). It must agree with the
 * seven daily reports, and a week that includes today is refused like a day that is not over.
 */
class WeeklyTotalsChallengeTest {

    static final Outlets OUTLETS = new Outlets();
    static final DailySalesReport REPORT = new DailySalesReport(new DemoSalesFeed(Fixture.CLOCK, OUTLETS), OUTLETS, Fixture.CLOCK);

    @Test
    void theWeekIsTheSumOfItsDaysHighestFirst() {
        LocalDate last = Fixture.DAY;
        Map<String, Long> week = REPORT.weekTotals(last);
        assertThat(week).hasSize(40);
        for (String outlet : OUTLETS.ids()) {
            long sum = 0;
            for (int i = 0; i < 7; i++) {
                sum += REPORT.forDay(last.minusDays(i)).outlets().stream().filter(o -> o.outletId().equals(outlet)).findFirst().orElseThrow().totalPaise();
            }
            assertThat(week.get(outlet)).as(outlet).isEqualTo(sum);
        }
        var totals = new ArrayList<>(week.values());
        assertThat(totals).isSortedAccordingTo(Comparator.reverseOrder());
    }

    @Test
    void aWeekEndingTodayIsNotOverYet() {
        assertThatThrownBy(() -> REPORT.weekTotals(Fixture.DAY.plusDays(1))).isInstanceOf(org.springframework.web.ErrorResponseException.class);
    }
}
