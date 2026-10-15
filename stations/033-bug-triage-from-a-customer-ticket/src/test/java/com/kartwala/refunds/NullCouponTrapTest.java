package com.kartwala.refunds;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The first test written for this ticket: it reproduces the customer's request on the old code before anything is
 * changed, then shows why last month's patch let the bug come back.
 */
class NullCouponTrapTest {

    static final Line JEANS = new Line("L1", "Denim jeans", 199_900);
    static final Line BELT = new Line("L2", "Leather belt", 59_900);

    @Test
    void theTicketsRequestThrowsOnTheOldCode() {
        OldOrder ticket = new OldOrder("KW-1042", List.of(JEANS, BELT), null);
        assertThatThrownBy(() -> OldRefundCalculator.refundable(ticket, List.of(BELT)))
                .isInstanceOf(NullPointerException.class)
                .hasMessageContaining("because the return value of \"com.kartwala.refunds.OldOrder.coupon()\" is null")
                .satisfies(e -> assertThat(e.getStackTrace()[0].getMethodName()).isEqualTo("couponShare"));
    }

    @Test
    void thePatchClosedTheTicketButTheBugCameBackOnAnotherPath() {
        OldOrder ticket = new OldOrder("KW-1042", List.of(JEANS, BELT), null);
        assertThat(OldRefundCalculator.patchedPartRefund(ticket, List.of(BELT))).isEqualTo(59_900);   // the symptom is gone
        assertThatThrownBy(() -> OldRefundCalculator.wholeOrderRefund(ticket)).isInstanceOf(NullPointerException.class);   // the cause is not
    }

    @Test
    void theFixIsInTheModelSoEveryPathIsSafe() {
        Order ticket = new Order("KW-1042", List.of(JEANS, BELT), null);
        assertThat(ticket.coupon()).isSameAs(Coupon.NONE);
        assertThat(RefundCalculator.amount(ticket, List.of(BELT), false, 0)).isEqualTo(59_900);
        assertThat(RefundCalculator.amount(ticket, List.of(JEANS, BELT), true, 0)).isEqualTo(259_800);
        assertThat(RefundCalculator.amount(ticket, List.of(JEANS), false, 0)).isEqualTo(199_900);
    }
}
