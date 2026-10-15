package com.kartwala.refunds;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/** Demo audit: one log line per decision. A real one would write to a table. */
@Component
class LoggingAudit implements EligibilityAudit {

    private static final Logger log = LoggerFactory.getLogger(LoggingAudit.class);

    @Override
    public void record(String orderId, Reason reason, RefundRules.Decision decision) {
        log.info("refund eligibility order={} reason={} eligible={} reasons={}", orderId, reason, decision.eligible(), decision.reasons());
    }
}
