package com.kartwala.refunds;

/** Records every decision, for support and disputes. A command: tests verify it was called. */
interface EligibilityAudit {
    void record(String orderId, Reason reason, RefundRules.Decision decision);
}
