package com.tijori.loans;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;

/**
 * The EMI formula and the amortisation schedule, in BigDecimal. A learning exercise, not financial advice:
 * real lenders also add fees, broken-period interest and their own rounding rules.
 */
final class Emi {

    /** 34 significant digits for every intermediate step: far more than paise need, so rounding happens only where we say. */
    static final MathContext MC = MathContext.DECIMAL128;

    record Row(int month, long emiPaise, long interestPaise, long principalPaise, long prepaidPaise, long balancePaise) {
    }

    private Emi() {
    }

    /** Monthly rate as a fraction: 12.99% a year is 0.1299 / 12 a month. */
    static BigDecimal monthlyRate(BigDecimal annualPercent) {
        return annualPercent.divide(BigDecimal.valueOf(1200), MC);
    }

    /** EMI = P x r x (1+r)^n / ((1+r)^n - 1), rounded half up to whole rupees, as most lenders quote it. In paise. */
    static long emiPaise(long principalPaise, BigDecimal annualPercent, int months) {
        BigDecimal p = BigDecimal.valueOf(principalPaise, 2);              // rupees, exactly
        BigDecimal r = monthlyRate(annualPercent);
        BigDecimal growth = BigDecimal.ONE.add(r).pow(months, MC);         // (1+r)^n
        BigDecimal emi = p.multiply(r, MC).multiply(growth, MC).divide(growth.subtract(BigDecimal.ONE), MC);
        return emi.setScale(0, RoundingMode.HALF_UP).movePointRight(2).longValueExact();
    }

    /**
     * Month by month: interest on what is still owed (rounded to the paisa), the rest of the EMI repays principal.
     * Because the EMI was rounded to a whole rupee, the last month would not land on zero; it is adjusted to pay
     * exactly what is left, interest included, so the loan closes at 0. A whole-rupee EMI rounded up can also
     * repay a small, long loan before its last month; then that month pays what is left and the schedule stops early.
     */
    static List<Row> schedule(long principalPaise, BigDecimal annualPercent, int months) {
        return schedule(principalPaise, annualPercent, months, 0, 0);
    }

    /**
     * Challenge 1: prepayPaise is paid after the EMI of prepayMonth. The EMI stays the same, so the balance reaches
     * zero sooner and the early-close rule ends the schedule. The caller checks the amount is less than the balance.
     */
    static List<Row> schedule(long principalPaise, BigDecimal annualPercent, int months, int prepayMonth, long prepayPaise) {
        long emi = emiPaise(principalPaise, annualPercent, months);
        BigDecimal r = monthlyRate(annualPercent);
        List<Row> rows = new ArrayList<>();
        long balance = principalPaise;
        for (int m = 1; m <= months && balance > 0; m++) {
            long interest = BigDecimal.valueOf(balance).multiply(r, MC).setScale(0, RoundingMode.HALF_UP).longValueExact();
            long principal = m == months ? balance : Math.min(emi - interest, balance);   // the final adjustment
            long prepaid = m == prepayMonth ? prepayPaise : 0;
            balance -= principal + prepaid;
            rows.add(new Row(m, interest + principal, interest, principal, prepaid, balance));
        }
        return rows;
    }
}
