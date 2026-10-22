package com.paysetu.payments;

import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.Optional;

/** The adapter for sim-alpha: our paise to its rupee text, its states and codes to our outcomes, its exceptions to ours. */
@Component
class AlphaProvider implements PaymentProvider {

    private final AlphaApi api;

    AlphaProvider(AlphaApi api) {
        this.api = api;
    }

    @Override
    public String name() {
        return "sim-alpha";
    }

    @Override
    public Outcome charge(String reference, long amountPaise) {
        try {
            return outcome(api.createCharge(reference, rupees(amountPaise)));
        } catch (AlphaApi.ConnectionRefused e) {
            throw new NotSent("sim-alpha refused the connection");
        } catch (AlphaApi.ReadTimeout e) {
            throw new Unknown("sim-alpha did not answer in time");
        }
    }

    @Override
    public Optional<Outcome> lookup(String reference) {
        try {
            return api.findByReference(reference).map(AlphaProvider::outcome);
        } catch (AlphaApi.ReadTimeout | AlphaApi.ConnectionRefused e) {
            throw new Unknown("sim-alpha's status check did not answer");
        }
    }

    @Override
    public String refund(String providerRef, long amountPaise) {
        try {
            return api.refund(providerRef, rupees(amountPaise));
        } catch (AlphaApi.ConnectionRefused e) {
            throw new NotSent("sim-alpha refused the connection");
        }
    }

    private static Outcome outcome(AlphaApi.AlphaCharge c) {
        if ("CAPTURED".equals(c.state())) {
            return new Outcome.Charged(c.chargeId());
        }
        return new Outcome.Declined(switch (c.errorCode()) {
            case "INSUFFICIENT_BALANCE" -> DeclineReason.INSUFFICIENT_FUNDS;
            case "CARD_BLOCKED" -> DeclineReason.CARD_BLOCKED;
            default -> DeclineReason.DECLINED_BY_PROVIDER;
        });
    }

    /** 123456 paise to "1234.56", exactly. */
    static String rupees(long paise) {
        return BigDecimal.valueOf(paise, 2).toPlainString();
    }
}
