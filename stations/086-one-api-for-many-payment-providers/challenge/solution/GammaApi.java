package com.paysetu.payments;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * The simulated provider "sim-gamma": a yes/no answer with a short reason word ("funds", "blocked", "risk"). Nothing is
 * charged. Demo rules of the simulation: the same amount endings as the other two decline.
 */
@Component
class GammaApi {

    record GammaPayment(String id, String ref, long paise, boolean ok, String reason) {
    }

    static final class Unreachable extends RuntimeException {
    }

    volatile boolean unreachable;
    final Map<String, GammaPayment> payments = new ConcurrentHashMap<>();
    final List<String> refunds = new CopyOnWriteArrayList<>();
    private final AtomicInteger ids = new AtomicInteger();

    GammaPayment pay(String ref, long paise) {
        if (unreachable) {
            throw new Unreachable();
        }
        return payments.computeIfAbsent(ref, r -> {
            String reason = paise % 100 == 51 ? "funds" : paise % 100 == 5 ? "blocked" : null;
            return new GammaPayment("g-" + ids.incrementAndGet(), r, paise, reason == null, reason);
        });
    }

    Optional<GammaPayment> get(String ref) {
        if (unreachable) {
            throw new Unreachable();
        }
        return Optional.ofNullable(payments.get(ref));
    }

    String refund(String id, long paise) {
        if (unreachable) {
            throw new Unreachable();
        }
        refunds.add(id + " " + paise);
        return "gr-" + ids.incrementAndGet();
    }

    void reset() {
        unreachable = false;
        payments.clear();
        refunds.clear();
        ids.set(0);
    }
}
