package com.paysetu.cards;

import org.springframework.stereotype.Component;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.YearMonth;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * The simulated card network's token service. In real life this is Visa, Mastercard or RuPay (often reached through a
 * payment aggregator): it keeps the card number in its own vault and gives the merchant a token. Here the "vault" is a
 * map inside the app, standing for the network's side; Paysetu's own code and database never keep the number.
 * Nothing is charged. Demo rules of the simulation: 4... is VISA, 5... MASTERCARD, 6... RUPAY; an amount ending in
 * 51 paise is declined.
 */
@Component
class SimNetwork {

    record Token(String tokenRef, String network, String last4) {
    }

    static final class Refused extends RuntimeException {
        Refused(String message) {
            super(message);
        }
    }

    private record Vaulted(String cardNumber, YearMonth expiry) {
    }

    private final Clock clock;
    private final SecureRandom random = new SecureRandom();
    private final Map<String, Vaulted> vault = new ConcurrentHashMap<>();
    private final Set<String> unusedCryptograms = ConcurrentHashMap.newKeySet();
    private final AtomicInteger ids = new AtomicInteger();

    SimNetwork(Clock clock) {
        this.clock = clock;
    }

    Token provision(String cardNumber, YearMonth expiry) {
        String network = switch (cardNumber.charAt(0)) {
            case '4' -> "VISA";
            case '5' -> "MASTERCARD";
            case '6' -> "RUPAY";
            default -> throw new Refused("This card network is not supported");
        };
        if (expiry.isBefore(YearMonth.now(clock.withZone(Cards.IST)))) {
            throw new Refused("This card has expired");
        }
        StringBuilder ref = new StringBuilder("tkn_");
        for (int i = 0; i < 20; i++) {
            ref.append((char) ('a' + random.nextInt(26)));
        }
        vault.put(ref.toString(), new Vaulted(cardNumber, expiry));
        return new Token(ref.toString(), network, cardNumber.substring(cardNumber.length() - 4));
    }

    /** A one-time value proving this payment comes from the token's owner, through its merchant. */
    String cryptogram(String tokenRef) {
        if (!vault.containsKey(tokenRef)) {
            throw new Refused("Unknown or deleted token");
        }
        String c = "cg_" + ids.incrementAndGet();
        unusedCryptograms.add(c);
        return c;
    }

    /** Returns the network's reference for an approved payment, or null for a decline. */
    String authorise(String tokenRef, String cryptogram, long amountPaise) {
        if (!vault.containsKey(tokenRef) || !unusedCryptograms.remove(cryptogram)) {
            throw new Refused("Token or cryptogram not valid");
        }
        return amountPaise % 100 == 51 ? null : "auth_" + ids.incrementAndGet();
    }

    void delete(String tokenRef) {
        vault.remove(tokenRef);
    }

    /** For tests: whether the network holds this card number (the network's side, not Paysetu's). */
    boolean holds(String cardNumber) {
        return vault.values().stream().anyMatch(v -> v.cardNumber().equals(cardNumber));
    }

    void reset() {
        vault.clear();
        unusedCryptograms.clear();
        ids.set(0);
    }
}
