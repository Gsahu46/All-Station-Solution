package com.paysetu.payments;

import org.springframework.stereotype.Component;

import java.util.Optional;

/** The adapter for sim-beta: its two-digit response codes to our outcomes, its exceptions to ours. */
@Component
class BetaProvider implements PaymentProvider {

    private final BetaApi api;

    BetaProvider(BetaApi api) {
        this.api = api;
    }

    @Override
    public String name() {
        return "sim-beta";
    }

    @Override
    public Outcome charge(String reference, long amountPaise) {
        try {
            return outcome(api.authorise(reference, amountPaise));
        } catch (BetaApi.ConnectFailed e) {
            throw new NotSent("sim-beta could not be reached");
        } catch (BetaApi.Timeout e) {
            throw new Unknown("sim-beta did not answer in time");
        }
    }

    @Override
    public Optional<Outcome> lookup(String reference) {
        try {
            return api.inquire(reference).map(BetaProvider::outcome);
        } catch (BetaApi.ConnectFailed | BetaApi.Timeout e) {
            throw new Unknown("sim-beta's status check did not answer");
        }
    }

    @Override
    public String refund(String providerRef, long amountPaise) {
        try {
            return api.reverse(providerRef, amountPaise);
        } catch (BetaApi.ConnectFailed e) {
            throw new NotSent("sim-beta could not be reached");
        }
    }

    static Outcome outcome(BetaApi.BetaReply r) {
        return switch (r.responseCode()) {
            case "00" -> new Outcome.Charged(r.txnId());
            case "51" -> new Outcome.Declined(DeclineReason.INSUFFICIENT_FUNDS);
            case "62" -> new Outcome.Declined(DeclineReason.CARD_BLOCKED);
            default -> new Outcome.Declined(DeclineReason.DECLINED_BY_PROVIDER);   // "05" do not honour, and codes we do not know
        };
    }
}
