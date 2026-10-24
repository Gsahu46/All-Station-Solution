package com.taskloom.support;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** The formats the redactor knows, and what it leaves alone. No Spring: plain strings. */
class RedactorTest {

    @Test
    void knownFormatsAndTheCustomersNameAreRemoved() {
        var r = Redactor.redact("Mail ANITA.rao@Example.co.in, call +91-98765-43210 or 09876543210, card 5555-5555-5555-4444, "
                + "Aadhaar 2345 6789 0123, PAN abcpr1234k. Thanks, anita RAO", "Anita Rao");
        assertThat(r.text()).isEqualTo("Mail [EMAIL], call [PHONE] or [PHONE], card [CARD], Aadhaar [AADHAAR], PAN [PAN]. Thanks, [CUSTOMER] [CUSTOMER]");
        assertThat(r.removed()).isEqualTo(Map.of("email", 1, "phone", 2, "card", 1, "aadhaar", 1, "pan", 1, "name", 2));
    }

    @Test
    void numbersThatAreNotCardsOrPhonesAreKept() {
        var r = Redactor.redact("Order 1234567812345678 failed with error 4031 at 10:30 on 2026-10-03; invoice ₹1,499.", "Anita Rao");
        assertThat(r.text()).isEqualTo("Order 1234567812345678 failed with error 4031 at 10:30 on 2026-10-03; invoice ₹1,499.");   // not a valid card number
        assertThat(r.removed()).isEmpty();
    }
}
