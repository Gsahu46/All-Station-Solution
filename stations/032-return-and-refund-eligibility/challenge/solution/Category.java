package com.kartwala.refunds;

import java.util.EnumSet;
import java.util.Set;

import static com.kartwala.refunds.Reason.CHANGED_MIND;
import static com.kartwala.refunds.Reason.DAMAGED;
import static com.kartwala.refunds.Reason.NOT_AS_DESCRIBED;
import static com.kartwala.refunds.Reason.SIZE_ISSUE;
import static com.kartwala.refunds.Reason.WRONG_ITEM;

/**
 * Each category's return window and accepted reasons, in one place (demo rules). The window and the reasons belong
 * to the category: changing electronics cannot change clothing, which is how the old switch statement broke it.
 */
enum Category {
    CLOTHING(30, EnumSet.of(DAMAGED, WRONG_ITEM, NOT_AS_DESCRIBED, CHANGED_MIND, SIZE_ISSUE)),
    ELECTRONICS(7, EnumSet.of(DAMAGED, WRONG_ITEM, NOT_AS_DESCRIBED)),
    BOOKS(10, EnumSet.of(DAMAGED, WRONG_ITEM, CHANGED_MIND)),
    GROCERY(2, EnumSet.of(DAMAGED, WRONG_ITEM)),
    FOOTWEAR(15, EnumSet.of(DAMAGED, WRONG_ITEM, CHANGED_MIND, SIZE_ISSUE));

    final int windowDays;
    final Set<Reason> reasons;

    /** Clothing and footwear: a customer's-choice return needs the tags attached. */
    boolean needsTags() {
        return this == CLOTHING || this == FOOTWEAR;
    }

    Category(int windowDays, Set<Reason> reasons) {
        this.windowDays = windowDays;
        this.reasons = reasons;
    }
}
