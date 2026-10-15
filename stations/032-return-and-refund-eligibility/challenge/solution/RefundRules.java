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

    /** Demo rule: festive deliveries of clothing and books can come back until 30 November. */
    static final LocalDate FESTIVE_FROM = LocalDate.of(2026, 10, 15);
    static final LocalDate FESTIVE_TO = LocalDate.of(2026, 11, 15);
    static final LocalDate FESTIVE_LAST_DAY = LocalDate.of(2026, 11, 30);

    record Decision(boolean eligible, List<String> reasons, long refundPaise, LocalDate lastDayToReturn) {
    }

    private RefundRules() {
    }

    static Decision check(Order order, Reason reason, Boolean tagsAttached, Boolean sealIntact, LocalDate today) {
        if (order.deliveredOn() == null) {
            return new Decision(false, List.of("NOT_DELIVERED"), 0, null);   // nothing to return yet: cancel instead
        }
        Category category = order.category();
        LocalDate lastDay = lastDay(category, order.deliveredOn());
        List<String> refused = new ArrayList<>();
        if (today.isAfter(lastDay)) {
            refused.add("WINDOW_CLOSED");
        }
        if (!category.reasons.contains(reason)) {
            refused.add("REASON_NOT_ACCEPTED");
        }
        if (category == Category.CLOTHING && order.hygieneItem() && reason != Reason.DAMAGED && reason != Reason.WRONG_ITEM) {
            refused.add("HYGIENE_ITEM");
        }
        if (category.needsTags() && !tagsAttached && reason.customersChoice) {
            refused.add("TAGS_REMOVED");
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

    static LocalDate lastDay(Category category, LocalDate deliveredOn) {
        LocalDate normal = deliveredOn.plusDays(category.windowDays);
        boolean festive = (category == Category.CLOTHING || category == Category.BOOKS)
                && !deliveredOn.isBefore(FESTIVE_FROM) && !deliveredOn.isAfter(FESTIVE_TO);
        return festive && FESTIVE_LAST_DAY.isAfter(normal) ? FESTIVE_LAST_DAY : normal;
    }
}
