package com.kartwala.refunds;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: the old suite had one happy-path test, and it never noticed. */
class HappyPathOnlyTrapTest {

    static final LocalDate TODAY = LocalDate.of(2026, 10, 15);

    @Test
    void theOldSuitesOnlyTestStillPassedAfterTheChange() {
        // The test that existed: electronics, three days after delivery. Green before and after the March change.
        assertThat(OldRefundRules.withinWindow(Category.ELECTRONICS, 3)).isTrue();
    }

    @Test
    void butClothingReturnedOnDay20WasRefusedByTheOldRule() {
        assertThat(OldRefundRules.withinWindow(Category.CLOTHING, 20)).isFalse();   // the bug customers hit
        Order kurta = new Order("KW-1001", "Cotton kurta", Category.CLOTHING, 129_900, TODAY.minusDays(20), false);
        RefundRules.Decision now = RefundRules.check(kurta, Reason.SIZE_ISSUE, true, null, TODAY);
        assertThat(now.eligible()).isTrue();
        assertThat(now.lastDayToReturn()).isEqualTo(TODAY.plusDays(10));
    }

    @Test
    void electronicsKeepsItsSevenDaysSoTheFixDidNotUndoTheChange() {
        Order phone = new Order("KW-1004", "Smartphone", Category.ELECTRONICS, 1_899_900, TODAY.minusDays(8), false);
        assertThat(RefundRules.check(phone, Reason.DAMAGED, null, true, TODAY).reasons()).containsExactly("WINDOW_CLOSED");
    }
}
