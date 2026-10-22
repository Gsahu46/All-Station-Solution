package com.paysetu.payments;

import org.springframework.stereotype.Component;

import java.util.Optional;

/** The adapter for sim-gamma. Adding a provider is this file, its SDK, a config value and a migration. */
@Component
class GammaProvider implements PaymentProvider {

    private final GammaApi api;

    GammaProvider(GammaApi api) {
        this.api = api;
    }

    @Override
    public String name() {
        return "sim-gamma";
    }

    @Override
    public Outcome charge(String reference, long amountPaise) {
        try {
            return outcome(api.pay(reference, amountPaise));
        } catch (GammaApi.Unreachable e) {
            throw new NotSent("sim-gamma could not be reached");
        }
    }

    @Override
    public Optional<Outcome> lookup(String reference) {
        try {
            return api.get(reference).map(GammaProvider::outcome);
        } catch (GammaApi.Unreachable e) {
            throw new Unknown("sim-gamma's status check did not answer");
        }
    }

    @Override
    public String refund(String providerRef, long amountPaise) {
        try {
            return api.refund(providerRef, amountPaise);
        } catch (GammaApi.Unreachable e) {
            throw new NotSent("sim-gamma could not be reached");
        }
    }

    private static Outcome outcome(GammaApi.GammaPayment p) {
        if (p.ok()) {
            return new Outcome.Charged(p.id());
        }
        return new Outcome.Declined(switch (p.reason()) {
            case "funds" -> DeclineReason.INSUFFICIENT_FUNDS;
            case "blocked" -> DeclineReason.CARD_BLOCKED;
            default -> DeclineReason.DECLINED_BY_PROVIDER;
        });
    }
}
