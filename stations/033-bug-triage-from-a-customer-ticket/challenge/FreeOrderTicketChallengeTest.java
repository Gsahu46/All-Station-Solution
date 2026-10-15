package com.kartwala.refunds;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: a second ticket. "Refund for my free samples fails." The log shows
 * java.lang.ArithmeticException: / by zero at com.kartwala.refunds.RefundCalculator.amount
 * for an order where every line was free (two ₹0 sample lines, no coupon). This is the failing test, written first.
 * Fix the cause so it passes, and keep every other test green.
 */
class FreeOrderTicketChallengeTest {

    static final Order SAMPLES = new Order("KW-1077", List.of(new Line("L1", "Sample serum", 0), new Line("L2", "Sample cream", 0)), null);

    @Test
    void aPartRefundOfAFreeOrderIsZeroNotAnError() {
        assertThat(RefundCalculator.amount(SAMPLES, List.of(SAMPLES.lines().get(0)), false, 0)).isZero();
    }

    @Test
    void theWholeFreeOrderIsZeroToo() {
        assertThat(RefundCalculator.amount(SAMPLES, SAMPLES.lines(), true, 0)).isZero();
    }
}
