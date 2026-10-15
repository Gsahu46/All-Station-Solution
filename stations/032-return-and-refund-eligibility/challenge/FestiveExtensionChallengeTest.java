package com.kartwala.refunds;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: festive season (demo rule). Clothing and books delivered from 15 October to 15 November 2026, both days
 * included, can be returned until 30 November 2026, or until their normal last day if that is later. Other
 * categories keep their normal window. Boundaries are where date bugs live: test the day before, the first and last
 * days, and the day after.
 */
class FestiveExtensionChallengeTest {

    @ParameterizedTest(name = "{0} delivered {1} -> last day {2}")
    @CsvSource(textBlock = """
            CLOTHING,    2026-10-14, 2026-11-13
            CLOTHING,    2026-10-15, 2026-11-30
            CLOTHING,    2026-11-15, 2026-12-15
            CLOTHING,    2026-11-16, 2026-12-16
            BOOKS,       2026-10-14, 2026-10-24
            BOOKS,       2026-10-15, 2026-11-30
            BOOKS,       2026-11-15, 2026-11-30
            BOOKS,       2026-11-16, 2026-11-26
            ELECTRONICS, 2026-10-20, 2026-10-27
            GROCERY,     2026-10-20, 2026-10-22
            """)
    void lastDayToReturn(Category category, LocalDate deliveredOn, LocalDate lastDay) {
        Order order = new Order("KW-3001", "item", category, 100_000, deliveredOn, false);
        RefundRules.Decision d = RefundRules.check(order, Reason.WRONG_ITEM, true, true, deliveredOn);
        assertThat(d.lastDayToReturn()).isEqualTo(lastDay);
    }

    @ParameterizedTest(name = "a book delivered on 20 October, checked on {0} -> eligible {1}")
    @CsvSource({"2026-11-30, true", "2026-12-01, false"})
    void theExtensionIsEnforcedNotJustShown(LocalDate today, boolean eligible) {
        Order novel = new Order("KW-3002", "Novel", Category.BOOKS, 39_900, LocalDate.of(2026, 10, 20), false);
        assertThat(RefundRules.check(novel, Reason.CHANGED_MIND, null, null, today).eligible()).isEqualTo(eligible);
    }
}
