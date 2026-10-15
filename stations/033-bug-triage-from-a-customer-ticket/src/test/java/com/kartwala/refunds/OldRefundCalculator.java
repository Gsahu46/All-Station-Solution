package com.kartwala.refunds;

import java.util.List;

/** The refund code before the fix, kept only in tests. */
final class OldRefundCalculator {

    private OldRefundCalculator() {
    }

    static long refundable(OldOrder order, List<Line> lines) {
        long linesTotal = total(lines);
        return linesTotal - couponShare(order, linesTotal);
    }

    static long couponShare(OldOrder order, long linesTotal) {
        return order.coupon().discountPaise() * linesTotal / total(order.lines());   // assumes every order has a coupon
    }

    /** Last month's fix for a ticket like this one: a null check where that ticket's request came in. */
    static long patchedPartRefund(OldOrder order, List<Line> lines) {
        if (order.coupon() == null) {
            return total(lines);
        }
        return refundable(order, lines);
    }

    /** The cancel-the-whole-order path, written later. It calls the calculator directly, as it should. */
    static long wholeOrderRefund(OldOrder order) {
        return refundable(order, order.lines());
    }

    static long total(List<Line> lines) {
        return lines.stream().mapToLong(Line::pricePaise).sum();
    }
}
