package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.EnumSource;

import java.time.LocalDate;
import java.util.Arrays;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Every rule, as a table. Pure function, no Spring: the whole class runs in milliseconds. One row per rule and per
 * category, so a change for one category that touches another turns a row red.
 */
class RefundRulesTest {

    static final LocalDate TODAY = LocalDate.of(2026, 10, 15);

    static Order order(Category category, int daysAgo, boolean hygiene) {
        return new Order("KW-1000", "item", category, 100_000, TODAY.minusDays(daysAgo), hygiene);
    }

    @ParameterizedTest(name = "{0} delivered {1} days ago, {2}, tags {3}, seal {4} -> {5}")
    @CsvSource(nullValues = "-", textBlock = """
            # category,  days, reason,           tags,  seal,  refused (| separated, empty = eligible)
            CLOTHING,    20,   SIZE_ISSUE,       true,  -,     ''
            CLOTHING,    30,   CHANGED_MIND,     true,  -,     ''
            CLOTHING,    31,   CHANGED_MIND,     true,  -,     WINDOW_CLOSED
            CLOTHING,    5,    CHANGED_MIND,     false, -,     TAGS_REMOVED
            CLOTHING,    5,    DAMAGED,          false, -,     ''
            CLOTHING,    40,   SIZE_ISSUE,       false, -,     WINDOW_CLOSED|TAGS_REMOVED
            ELECTRONICS, 7,    NOT_AS_DESCRIBED, -,     true,  ''
            ELECTRONICS, 8,    DAMAGED,          -,     true,  WINDOW_CLOSED
            ELECTRONICS, 2,    CHANGED_MIND,     -,     true,  REASON_NOT_ACCEPTED
            ELECTRONICS, 2,    WRONG_ITEM,       -,     false, SEAL_BROKEN
            ELECTRONICS, 2,    DAMAGED,          -,     false, ''
            BOOKS,       10,   CHANGED_MIND,     -,     -,     ''
            BOOKS,       11,   WRONG_ITEM,       -,     -,     WINDOW_CLOSED
            BOOKS,       3,    SIZE_ISSUE,       -,     -,     REASON_NOT_ACCEPTED
            GROCERY,     2,    DAMAGED,          -,     -,     ''
            GROCERY,     3,    DAMAGED,          -,     -,     WINDOW_CLOSED
            GROCERY,     1,    CHANGED_MIND,     -,     -,     REASON_NOT_ACCEPTED
            """)
    void theRuleTable(Category category, int daysAgo, Reason reason, Boolean tags, Boolean seal, String refused) {
        RefundRules.Decision d = RefundRules.check(order(category, daysAgo, false), reason, tags, seal, TODAY);
        List<String> expected = refused.isEmpty() ? List.of() : Arrays.asList(refused.split("\\|"));
        assertThat(d.reasons()).containsExactlyElementsOf(expected);
        assertThat(d.eligible()).isEqualTo(expected.isEmpty());
    }

    @ParameterizedTest
    @EnumSource(Category.class)
    void theLastDayIsOpenAndTheNextDayIsClosedInEveryCategory(Category category) {
        Reason accepted = Reason.WRONG_ITEM;   // accepted in every category, and not affected by tags or seal
        int window = category.windowDays;
        assertThat(RefundRules.check(order(category, window, false), accepted, true, true, TODAY).eligible()).isTrue();
        assertThat(RefundRules.check(order(category, window + 1, false), accepted, true, true, TODAY).reasons()).containsExactly("WINDOW_CLOSED");
    }

    @ParameterizedTest
    @CsvSource({"DAMAGED, true", "WRONG_ITEM, true", "NOT_AS_DESCRIBED, false", "CHANGED_MIND, false", "SIZE_ISSUE, false"})
    void hygieneItemsComeBackOnlyWhenItWasOurFault(Reason reason, boolean eligible) {
        assertThat(RefundRules.check(order(Category.CLOTHING, 3, true), reason, true, null, TODAY).eligible()).isEqualTo(eligible);
    }

    @Test
    void theCustomersChoicePaysThePickupFeeAndOurMistakeDoesNot() {
        assertThat(RefundRules.check(order(Category.CLOTHING, 3, false), Reason.CHANGED_MIND, true, null, TODAY).refundPaise()).isEqualTo(95_100);
        assertThat(RefundRules.check(order(Category.CLOTHING, 3, false), Reason.DAMAGED, true, null, TODAY).refundPaise()).isEqualTo(100_000);
        Order cheap = new Order("KW-1000", "bookmark", Category.BOOKS, 3_000, TODAY, false);
        assertThat(RefundRules.check(cheap, Reason.CHANGED_MIND, null, null, TODAY).refundPaise()).isZero();   // never negative
    }

    @Test
    void anOrderNotYetDeliveredCannotBeReturned() {
        Order undelivered = new Order("KW-1000", "Novel", Category.BOOKS, 39_900, null, false);
        assertThat(RefundRules.check(undelivered, Reason.CHANGED_MIND, null, null, TODAY))
                .returns(false, RefundRules.Decision::eligible)
                .returns(List.of("NOT_DELIVERED"), RefundRules.Decision::reasons)
                .returns(null, RefundRules.Decision::lastDayToReturn);
    }
}
