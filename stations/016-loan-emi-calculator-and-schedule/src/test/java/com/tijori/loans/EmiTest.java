package com.tijori.loans;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** The formula against a known value, every schedule closing at zero, and rate dates at their boundaries. */
class EmiTest {

    @Test
    void aTextbookExample() {
        // Rs 1,00,000 at 12% a year for 12 months: EMI Rs 8,884.88, quoted as Rs 8,885.
        assertThat(Emi.emiPaise(10_000_000, new BigDecimal("12"), 12)).isEqualTo(888_500);
    }

    @Test
    void everyCombinationClosesAtZeroAndRepaysThePrincipalExactly() {
        for (long principal : new long[]{1_000_000, 12_345_678, 50_000_000, 1_000_000_000}) {
            for (String rate : new String[]{"8.50", "12.99", "13.50", "24"}) {
                for (int months : new int[]{6, 7, 24, 60, 360}) {
                    List<Emi.Row> rows = Emi.schedule(principal, new BigDecimal(rate), months);
                    assertThat(rows.getLast().balancePaise()).as(principal + " " + rate + " " + months).isZero();
                    assertThat(rows.stream().mapToLong(Emi.Row::principalPaise).sum()).isEqualTo(principal);
                    assertThat(rows).allMatch(r -> r.balancePaise() >= 0);
                }
            }
        }
    }

    @Test
    void aSmallLongLoanWhoseEmiWasRoundedUpClosesEarlyInsteadOfGoingNegative() {
        // Rs 10,000 at 12.99% for 360 months: Rs 110.54 a month is quoted as Rs 111, so it is repaid by month 344.
        List<Emi.Row> rows = Emi.schedule(1_000_000, new BigDecimal("12.99"), 360);
        assertThat(rows).hasSize(344);
        assertThat(rows.getLast().balancePaise()).isZero();
        assertThat(rows.getLast().emiPaise()).isLessThan(11_100);
    }

    @Test
    void theRateIsTheOneValidOnTheDay() {
        RateTable table = new RateTable(Map.of(Product.PERSONAL, List.of(
                new RateTable.DatedRate(LocalDate.of(2026, 4, 1), new BigDecimal("13.50")),
                new RateTable.DatedRate(LocalDate.of(2026, 10, 1), new BigDecimal("12.99")))));
        assertThat(table.rateOn(Product.PERSONAL, LocalDate.of(2026, 3, 31))).isEmpty();
        assertThat(table.rateOn(Product.PERSONAL, LocalDate.of(2026, 9, 30)).orElseThrow().annualPercent()).isEqualByComparingTo("13.50");
        assertThat(table.rateOn(Product.PERSONAL, LocalDate.of(2026, 10, 1)).orElseThrow().annualPercent()).isEqualByComparingTo("12.99");
        assertThat(table.rateOn(Product.HOME, LocalDate.of(2026, 10, 1))).isEmpty();
    }
}
