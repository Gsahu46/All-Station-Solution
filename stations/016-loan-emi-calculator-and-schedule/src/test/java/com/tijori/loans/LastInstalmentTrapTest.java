package com.tijori.loans;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bugs before the fix.
 * A Rs 5,00,000 personal loan at 12.99% a year, over 24 months.
 */
class LastInstalmentTrapTest {

    static final long PRINCIPAL = 50_000_000;
    static final BigDecimal RATE = new BigDecimal("12.99");

    /** The "before" schedule: the same rounded EMI every month, including the last. Kept only in tests. */
    static long oldFinalBalance() {
        long emi = Emi.emiPaise(PRINCIPAL, RATE, 24);
        BigDecimal r = Emi.monthlyRate(RATE);
        long balance = PRINCIPAL;
        for (int m = 1; m <= 24; m++) {
            long interest = BigDecimal.valueOf(balance).multiply(r).setScale(0, RoundingMode.HALF_UP).longValueExact();
            balance -= emi - interest;
        }
        return balance;
    }

    @Test
    void theSameEmiEveryMonthNeverLandsOnZero() {
        assertThat(oldFinalBalance()).isEqualTo(-1_191);   // the customer overpays Rs 11.91 and the loan shows a negative balance
    }

    /** The "before" EMI: a calculator that keeps four decimals and rounds (1+r)^24 = 1.294862 to 1.2949 before dividing. */
    static long oldEmiPaise() {
        BigDecimal r = Emi.monthlyRate(RATE);
        BigDecimal growth = BigDecimal.ONE.add(r).pow(24).setScale(4, RoundingMode.HALF_UP);
        BigDecimal emi = BigDecimal.valueOf(PRINCIPAL, 2).multiply(r).multiply(growth)
                .divide(growth.subtract(BigDecimal.ONE), 10, RoundingMode.HALF_UP);
        return emi.setScale(0, RoundingMode.HALF_UP).movePointRight(2).longValueExact();
    }

    @Test
    void roundingAnIntermediateStepMovesTheEmiByThreeRupees() {
        assertThat(oldEmiPaise()).isEqualTo(2_376_600);                       // Rs 23,766: what the app showed
        assertThat(Emi.emiPaise(PRINCIPAL, RATE, 24)).isEqualTo(2_376_900);   // Rs 23,769: what the bank charges
    }

    @Test
    void theRealScheduleAdjustsTheLastInstalmentAndClosesAtZero() {
        List<Emi.Row> rows = Emi.schedule(PRINCIPAL, RATE, 24);
        assertThat(rows).hasSize(24);
        assertThat(rows.getLast().balancePaise()).isZero();
        assertThat(rows.getLast().emiPaise()).isEqualTo(2_376_900 - 1_191);   // the overpayment is taken off the last EMI
        assertThat(rows.stream().mapToLong(Emi.Row::principalPaise).sum()).isEqualTo(PRINCIPAL);
    }
}
