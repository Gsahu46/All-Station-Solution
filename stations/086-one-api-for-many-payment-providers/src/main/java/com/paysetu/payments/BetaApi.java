package com.paysetu.payments;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * The simulated provider "sim-beta", shaped like a card-network style API: amounts in paise, two-digit response codes
 * ("00" approved, "51" insufficient funds, "05" do not honour, "62" restricted card). Nothing is charged: an
 * authorisation is an entry in a map. Demo rules of the simulation: the same amount endings as sim-alpha decline.
 */
@Component
class BetaApi {

    record BetaReply(String txnId, String orderRef, long paise, String responseCode) {
    }

    static final class ConnectFailed extends RuntimeException {
    }

    static final class Timeout extends RuntimeException {
    }

    volatile boolean down;
    volatile boolean timeoutAfterAuthorising;
    final Map<String, BetaReply> authorisations = new ConcurrentHashMap<>();
    final List<String> reversals = new CopyOnWriteArrayList<>();
    private final AtomicInteger ids = new AtomicInteger(5000);

    BetaReply authorise(String orderRef, long paise) {
        if (down) {
            throw new ConnectFailed();
        }
        BetaReply r = authorisations.computeIfAbsent(orderRef, o ->
                new BetaReply("T" + ids.incrementAndGet(), o, paise, paise % 100 == 51 ? "51" : paise % 100 == 5 ? "05" : "00"));
        if (timeoutAfterAuthorising) {
            throw new Timeout();
        }
        return r;
    }

    Optional<BetaReply> inquire(String orderRef) {
        if (down) {
            throw new ConnectFailed();
        }
        return Optional.ofNullable(authorisations.get(orderRef));
    }

    String reverse(String txnId, long paise) {
        if (down) {
            throw new ConnectFailed();
        }
        reversals.add(txnId + " " + paise);
        return "R" + ids.incrementAndGet();
    }

    void reset() {
        down = false;
        timeoutAfterAuthorising = false;
        authorisations.clear();
        reversals.clear();
        ids.set(5000);
    }
}
