package com.kartwala.refunds;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** The amounts, without Spring. */
class RefundCalculatorTest {

    static final Line KURTA = new Line("L1", "Cotton kurta", 129_900);
    static final Line DUPATTA = new Line("L2", "Dupatta", 49_900);
    static final Order WITH_COUPON = new Order("KW-1041", List.of(KURTA, DUPATTA), new Coupon("FEST200", 20_000));

    @Test
    void aLineGivesBackItsPriceMinusItsShareOfTheCoupon() {
        // 20,000 x 49,900 / 179,800 = 5,550.6 paise of coupon, rounded down to 5,550.
        assertThat(RefundCalculator.amount(WITH_COUPON, List.of(DUPATTA), false, 0)).isEqualTo(44_350);
    }

    @Test
    void theLastRefundTakesWhatIsLeftSoTheTotalIsExactlyWhatWasPaid() {
        long first = RefundCalculator.amount(WITH_COUPON, List.of(DUPATTA), false, 0);
        long last = RefundCalculator.amount(WITH_COUPON, List.of(KURTA), true, first);
        assertThat(first + last).isEqualTo(WITH_COUPON.paidPaise()).isEqualTo(159_800);
        assertThat(last).isEqualTo(115_450);
    }

    @Test
    void aMissingCouponIsNoCouponForEveryCaller() {
        Order noCoupon = new Order("KW-1042", List.of(KURTA), null);
        assertThat(noCoupon.coupon().discountPaise()).isZero();
        assertThat(noCoupon.paidPaise()).isEqualTo(129_900);
    }
}
