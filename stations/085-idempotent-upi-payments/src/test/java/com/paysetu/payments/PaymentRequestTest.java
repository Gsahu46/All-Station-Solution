package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import java.util.Locale;

import static org.assertj.core.api.Assertions.assertThat;

/** Plain unit tests for the fingerprint rules. No Spring, no database: they run in milliseconds. */
class PaymentRequestTest {

    private static PaymentRequest req(String payer, String payee, long paise, String note) {
        return new PaymentRequest(payer, payee, paise, note);
    }

    @Test
    void vpaCaseDoesNotChangeTheFingerprint() {
        assertThat(req("ASHA@OKPAYSETU", "Ravi@OkSbi", 12550, "x").fingerprint())
                .isEqualTo(req("asha@okpaysetu", "ravi@oksbi", 12550, "x").fingerprint());
    }

    @Test
    void aTurkishServerLocaleDoesNotChangeTheFingerprint() {
        Locale original = Locale.getDefault();
        try {
            Locale.setDefault(Locale.forLanguageTag("tr-TR")); // here "I".toLowerCase() is a dotless "ı"
            assertThat(req("ISHAAN@OKICICI", "ravi@oksbi", 100, null).fingerprint())
                    .isEqualTo(req("ishaan@okicici", "ravi@oksbi", 100, null).fingerprint());
        } finally {
            Locale.setDefault(original);
        }
    }

    @Test
    void aMissingNoteAndAnEmptyNoteAreTheSamePayment() {
        assertThat(req("asha@okpaysetu", "ravi@oksbi", 12550, null).fingerprint())
                .isEqualTo(req("asha@okpaysetu", "ravi@oksbi", 12550, "").fingerprint());
    }

    @Test
    void anyWrittenNoteIsPartOfThePayment() {
        String none = req("asha@okpaysetu", "ravi@oksbi", 12550, null).fingerprint();
        assertThat(req("asha@okpaysetu", "ravi@oksbi", 12550, " ").fingerprint()).isNotEqualTo(none);
        assertThat(req("asha@okpaysetu", "ravi@oksbi", 12550, "Dinner").fingerprint()).isNotEqualTo(none);
    }

    @Test
    void everyPaymentFieldChangesTheFingerprint() {
        String base = req("asha@okpaysetu", "ravi@oksbi", 12550, "Dinner").fingerprint();
        assertThat(req("meera@okhdfc", "ravi@oksbi", 12550, "Dinner").fingerprint()).isNotEqualTo(base);
        assertThat(req("asha@okpaysetu", "kiran@okaxis", 12550, "Dinner").fingerprint()).isNotEqualTo(base);
        assertThat(req("asha@okpaysetu", "ravi@oksbi", 12551, "Dinner").fingerprint()).isNotEqualTo(base);
        assertThat(req("asha@okpaysetu", "ravi@oksbi", 12550, "Lunch").fingerprint()).isNotEqualTo(base);
    }
}
