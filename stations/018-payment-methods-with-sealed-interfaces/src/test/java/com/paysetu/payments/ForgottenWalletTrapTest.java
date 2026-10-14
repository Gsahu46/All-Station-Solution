package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bugs before the fix. */
class ForgottenWalletTrapTest extends ApiTest {

    /** The "before" model: one class, a nullable field per method. Kept only in tests. */
    record OldPayment(String vpa, String cardLast4, String bankCode, String walletMobile) {
    }

    /** The "before" refund path. It compiles, and nothing says wallets are missing. */
    static String oldRefundRoute(OldPayment p) {
        if (p.vpa() != null) {
            return "UPI " + p.vpa();
        } else if (p.cardLast4() != null) {
            return "card " + p.cardLast4();
        } else if (p.bankCode() != null) {
            return "bank " + p.bankCode();
        }
        return null;   // wallets were added later; nobody came back here
    }

    @Test
    void theOldRefundPathSilentlyForgetsWallets() {
        assertThat(oldRefundRoute(new OldPayment(null, null, null, "9876543210"))).isNull();
    }

    @Test
    void theOldClassAcceptsAPaymentThatIsTwoMethodsAtOnce() {
        // UPI and a card in one payment: the old code just picks whichever if comes first.
        assertThat(oldRefundRoute(new OldPayment("asha@okaxis", "4242", null, null))).isEqualTo("UPI asha@okaxis");
    }

    @Test
    void theSealedModelRefundsWalletsAndRefusesMixedMethods() throws Exception {
        intent("{\"type\":\"WALLET\",\"mobile\":\"9876543210\"}")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.refundRoute").value("Back to the Paysetu wallet of 98******10."));
        intent("{\"type\":\"UPI\",\"vpa\":\"asha@okaxis\",\"last4\":\"4242\"}").andExpect(status().isBadRequest());
    }
}
