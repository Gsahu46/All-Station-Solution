package com.kartwala.refunds;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * The refund rules as one pure function: no Spring, no clock, no database. Everything it needs is a parameter, so a
 * table of cases can test every category and reason in milliseconds. Returns every reason a return is refused.
 */
final class RefundRules {

    /** Demo rule: a return the customer chose (changed mind, size) pays ₹49 for the pickup. */
    static final long PICKUP_FEE_PAISE = 4_900;

    record Decision(boolean eligible, List<String> reasons, long refundPaise, LocalDate lastDayToReturn) {
    }

    private RefundRules() {
    }

    static Decision check(Order order, Reason reason, Boolean tagsAttached, Boolean sealIntact, LocalDate today) {
        if (order.deliveredOn() == null) {
            return new Decision(false, List.of("NOT_DELIVERED"), 0, null);   // nothing to return yet: cancel instead
        }
        Category category = order.category();
        LocalDate lastDay = order.deliveredOn().plusDays(category.windowDays);
        List<String> refused = new ArrayList<>();
        if (today.isAfter(lastDay)) {
            refused.add("WINDOW_CLOSED");
        }
        if (!category.reasons.contains(reason)) {
            refused.add("REASON_NOT_ACCEPTED");
        }
        if (category == Category.CLOTHING) {
            if (order.hygieneItem() && reason != Reason.DAMAGED && reason != Reason.WRONG_ITEM) {
                refused.add("HYGIENE_ITEM");
            }
            if (!tagsAttached && reason.customersChoice) {
                refused.add("TAGS_REMOVED");
            }
        }
        if (category == Category.ELECTRONICS && !sealIntact && reason != Reason.DAMAGED) {
            refused.add("SEAL_BROKEN");
        }
        if (!refused.isEmpty()) {
            return new Decision(false, List.copyOf(refused), 0, lastDay);
        }
        long fee = reason.customersChoice ? PICKUP_FEE_PAISE : 0;
        return new Decision(true, List.of(), Math.max(0, order.pricePaise() - fee), lastDay);
    }
}
