package com.paysetu.payments;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * The simulated provider "sim-alpha", shaped like its SDK would be: amounts in rupees as text, states CAPTURED and
 * FAILED, its own error codes. Nothing is charged: a charge is an entry in a map. Tests switch its behaviour.
 * Demo rules of the simulation: an amount ending in 51 paise is declined for balance, ending in 05 for a blocked card;
 * ending in 97 it charges and then times out, ending in 98 it refuses the connection (so the captures can show both).
 */
@Component
class AlphaApi {

    enum Fault { NONE, CONNECTION_REFUSED, TIMEOUT_BEFORE_CHARGING, TIMEOUT_AFTER_CHARGING }

    record AlphaCharge(String chargeId, String reference, String amount, String state, String errorCode) {
    }

    static final class ConnectionRefused extends RuntimeException {
    }

    static final class ReadTimeout extends RuntimeException {
    }

    volatile Fault fault = Fault.NONE;
    volatile boolean lookupDown;
    final Map<String, AlphaCharge> charges = new ConcurrentHashMap<>();
    final List<String> refunds = new CopyOnWriteArrayList<>();
    private final AtomicInteger ids = new AtomicInteger();

    AlphaCharge createCharge(String reference, String amountRupees) {
        Fault fault = this.fault != Fault.NONE ? this.fault
                : amountRupees.endsWith(".97") ? Fault.TIMEOUT_AFTER_CHARGING : amountRupees.endsWith(".98") ? Fault.CONNECTION_REFUSED : Fault.NONE;
        if (fault == Fault.CONNECTION_REFUSED) {
            throw new ConnectionRefused();
        }
        if (fault == Fault.TIMEOUT_BEFORE_CHARGING) {
            throw new ReadTimeout();
        }
        AlphaCharge c = charges.computeIfAbsent(reference, r -> {
            String code = amountRupees.endsWith(".51") ? "INSUFFICIENT_BALANCE" : amountRupees.endsWith(".05") ? "CARD_BLOCKED" : null;
            return new AlphaCharge("ch_" + ids.incrementAndGet(), r, amountRupees, code == null ? "CAPTURED" : "FAILED", code);
        });
        if (fault == Fault.TIMEOUT_AFTER_CHARGING) {
            throw new ReadTimeout();   // charged, but the answer never arrives
        }
        return c;
    }

    Optional<AlphaCharge> findByReference(String reference) {
        if (lookupDown) {
            throw new ReadTimeout();
        }
        return Optional.ofNullable(charges.get(reference));
    }

    String refund(String chargeId, String amountRupees) {
        if (fault == Fault.CONNECTION_REFUSED) {
            throw new ConnectionRefused();
        }
        refunds.add(chargeId + " " + amountRupees);
        return "rf_" + ids.incrementAndGet();
    }

    void reset() {
        fault = Fault.NONE;
        lookupDown = false;
        charges.clear();
        refunds.clear();
        ids.set(0);
    }
}
