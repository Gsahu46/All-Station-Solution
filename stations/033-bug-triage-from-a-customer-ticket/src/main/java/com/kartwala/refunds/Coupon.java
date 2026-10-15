package com.kartwala.refunds;

/** A coupon applied to the whole order. NONE stands for "no coupon", so no code ever meets a null coupon. */
record Coupon(String code, long discountPaise) {

    static final Coupon NONE = new Coupon("", 0);
}
