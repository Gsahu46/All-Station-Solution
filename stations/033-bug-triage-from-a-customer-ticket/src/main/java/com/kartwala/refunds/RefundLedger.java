package com.kartwala.refunds;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Refund records, in memory (demo). A record is created; no money moves. The failure switch exists for the failure
 * drill: it makes the ledger fail the way a real one does when its database is down.
 */
@Component
class RefundLedger {

    record Refund(String refundId, String orderId, List<String> lineIds, long amountPaise) {
    }

    private final Map<String, List<Refund>> byOrder = new ConcurrentHashMap<>();
    private final AtomicLong sequence = new AtomicLong(5000);
    private volatile boolean simulateFailure;

    RefundLedger(@Value("${kartwala.refunds.simulate-ledger-failure:false}") boolean simulateFailure) {
        this.simulateFailure = simulateFailure;
    }

    List<Refund> forOrder(String orderId) {
        failIfDrill();
        return List.copyOf(byOrder.getOrDefault(orderId, List.of()));
    }

    Refund record(String orderId, List<String> lineIds, long amountPaise) {
        failIfDrill();
        Refund refund = new Refund("RF-" + sequence.incrementAndGet(), orderId, List.copyOf(lineIds), amountPaise);
        byOrder.computeIfAbsent(orderId, id -> new ArrayList<>()).add(refund);
        return refund;
    }

    void simulateFailure(boolean on) {
        simulateFailure = on;
    }

    private void failIfDrill() {
        if (simulateFailure) {
            throw new IllegalStateException("Refund ledger did not answer (failure drill)");
        }
    }
}
