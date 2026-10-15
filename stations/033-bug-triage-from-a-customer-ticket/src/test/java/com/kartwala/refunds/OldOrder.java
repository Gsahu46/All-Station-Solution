package com.kartwala.refunds;

import java.util.List;

/** The order as it was before the fix, kept only in tests: no coupon meant a null coupon. */
record OldOrder(String id, List<Line> lines, Coupon coupon) {
}
