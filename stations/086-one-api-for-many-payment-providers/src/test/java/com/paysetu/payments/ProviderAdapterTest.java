package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The adapters and the factory alone, no Spring: each provider's dialect becomes the same outcomes. */
class ProviderAdapterTest {

    final AlphaProvider alpha = new AlphaProvider(new AlphaApi());
    final BetaProvider beta = new BetaProvider(new BetaApi());

    @Test
    void bothProvidersErrorsMapToTheSameReasons() {
        assertThat(alpha.charge("a1", 249951)).isEqualTo(new PaymentProvider.Outcome.Declined(PaymentProvider.DeclineReason.INSUFFICIENT_FUNDS));
        assertThat(beta.charge("b1", 249951)).isEqualTo(new PaymentProvider.Outcome.Declined(PaymentProvider.DeclineReason.INSUFFICIENT_FUNDS));
        assertThat(alpha.charge("a2", 249905)).isEqualTo(new PaymentProvider.Outcome.Declined(PaymentProvider.DeclineReason.CARD_BLOCKED));
        assertThat(BetaProvider.outcome(new BetaApi.BetaReply("T1", "b", 1, "62"))).isEqualTo(new PaymentProvider.Outcome.Declined(PaymentProvider.DeclineReason.CARD_BLOCKED));
        assertThat(beta.charge("b2", 249905)).isEqualTo(new PaymentProvider.Outcome.Declined(PaymentProvider.DeclineReason.DECLINED_BY_PROVIDER));   // "05" do not honour
        assertThat(BetaProvider.outcome(new BetaApi.BetaReply("T1", "b", 1, "N7"))).isEqualTo(new PaymentProvider.Outcome.Declined(PaymentProvider.DeclineReason.DECLINED_BY_PROVIDER));
        assertThat(AlphaProvider.rupees(5)).isEqualTo("0.05");
    }

    @Test
    void timeoutsAreUnknownAndRefusedConnectionsAreNotSent() {
        AlphaApi api = new AlphaApi();
        AlphaProvider p = new AlphaProvider(api);
        api.fault = AlphaApi.Fault.TIMEOUT_AFTER_CHARGING;
        assertThatThrownBy(() -> p.charge("a1", 100)).isInstanceOf(PaymentProvider.Unknown.class);
        api.fault = AlphaApi.Fault.CONNECTION_REFUSED;
        assertThatThrownBy(() -> p.charge("a2", 100)).isInstanceOf(PaymentProvider.NotSent.class);
        assertThat(p.lookup("a1")).contains(new PaymentProvider.Outcome.Charged("ch_1"));
        assertThat(p.lookup("a2")).isEmpty();
    }

    @Test
    void providersArePickedByNameAndAWrongNameStopsTheStart() {
        assertThat(new Providers(List.of(alpha, beta), "sim-beta", "sim-alpha").inOrder()).containsExactly(beta, alpha);
        assertThat(new Providers(List.of(alpha, beta), "sim-alpha", "").inOrder()).containsExactly(alpha);
        assertThatThrownBy(() -> new Providers(List.of(alpha, beta), "sim-omega", ""))
                .hasMessage("No payment provider named sim-omega; known: [sim-alpha, sim-beta]");
    }
}
