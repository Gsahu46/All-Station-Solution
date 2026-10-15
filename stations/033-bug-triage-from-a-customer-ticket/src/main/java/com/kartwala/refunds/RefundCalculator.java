package com.kartwala.refunds;

import java.util.List;

/**
 * How much comes back for some lines of an order: their prices minus their share of the coupon, in proportion to
 * price. The share is rounded down, so a part refund can be a fraction of a paisa generous; the refund that empties
 * the order gets exactly what is left of what was paid, so the refunds of an order always add up to what was paid.
 */
final class RefundCalculator {

    private RefundCalculator() {
    }

    static long amount(Order order, List<Line> lines, boolean lastLinesOfTheOrder, long alreadyRefundedPaise) {
        if (lastLinesOfTheOrder) {
            return order.paidPaise() - alreadyRefundedPaise;
        }
        long linesTotal = lines.stream().mapToLong(Line::pricePaise).sum();
        long couponShare = Math.multiplyExact(order.coupon().discountPaise(), linesTotal) / order.itemsTotalPaise();
        return linesTotal - couponShare;
    }
}
