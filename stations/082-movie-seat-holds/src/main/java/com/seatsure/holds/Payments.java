package com.seatsure.holds;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Simulated payment provider: nothing is charged, a reference is recorded. A charge takes a while, like a real one, and is idempotent by hold id
 * (a retry returns the same reference). shortcut: in memory; station 085 shows a real idempotency store.
 */
@Component
class Payments {

    private final Map<String, String> charges = new ConcurrentHashMap<>();
    final Map<String, String> refunds = new ConcurrentHashMap<>();
    volatile Duration delay;

    Payments(@Value("${seatsure.payment-delay}") Duration delay) {
        this.delay = delay;
    }

    String charge(String holdId, long amountPaise) {
        try {
            Thread.sleep(delay);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
        return charges.computeIfAbsent(holdId, id -> "pay_" + id.substring(0, 8));
    }

    void refund(String holdId) {
        refunds.put(holdId, charges.get(holdId));
    }
}
