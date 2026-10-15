package com.kartwala.refunds;

import java.util.List;
import java.util.Optional;

/**
 * An order and what was paid. The root cause of the ticket was here: an order without a coupon had a null coupon,
 * and every piece of code that read it had to remember. Now the constructor turns null into Coupon.NONE, once, so
 * no caller can forget, including callers written next year.
 */
record Order(String id, List<Line> lines, Coupon coupon) {

    Order {
        lines = List.copyOf(lines);
        coupon = coupon == null ? Coupon.NONE : coupon;
    }

    long itemsTotalPaise() {
        return lines.stream().mapToLong(Line::pricePaise).sum();
    }

    long paidPaise() {
        return itemsTotalPaise() - coupon.discountPaise();
    }

    Optional<Line> line(String lineId) {
        return lines.stream().filter(l -> l.id().equals(lineId)).findFirst();
    }
}
