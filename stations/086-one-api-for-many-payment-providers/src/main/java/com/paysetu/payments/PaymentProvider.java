package com.paysetu.payments;

import java.util.Optional;

/**
 * What the rest of the code knows about a payment provider. Each provider's own request shapes, amounts and error
 * codes stay inside its adapter; nothing outside this package's adapters names a provider's SDK.
 */
interface PaymentProvider {

    /** The name used in configuration and stored on each payment, e.g. "sim-alpha". */
    String name();

    /**
     * Charges once for this reference. Returns the answer, or throws {@link NotSent} when the request certainly never
     * reached the provider, or {@link Unknown} when it may have (a timeout): then nobody knows yet whether it charged.
     */
    Outcome charge(String reference, long amountPaise);

    /** Asks the provider what happened to this reference. Empty: it has no such charge. Throws {@link Unknown} if it cannot say. */
    Optional<Outcome> lookup(String reference);

    /** Refunds part or all of a charge this provider made; throws {@link NotSent} when the request never reached it. */
    String refund(String providerRef, long amountPaise);

    enum DeclineReason { INSUFFICIENT_FUNDS, CARD_BLOCKED, DECLINED_BY_PROVIDER }

    sealed interface Outcome {
        record Charged(String providerRef) implements Outcome {
        }

        record Declined(DeclineReason reason) implements Outcome {
        }
    }

    final class NotSent extends RuntimeException {
        NotSent(String message) {
            super(message);
        }
    }

    final class Unknown extends RuntimeException {
        Unknown(String message) {
            super(message);
        }
    }
}
