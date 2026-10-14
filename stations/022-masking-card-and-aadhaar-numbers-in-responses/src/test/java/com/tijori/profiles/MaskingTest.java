package com.tijori.profiles;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Each masking rule, and toString, which is what logs print. */
class MaskingTest {

    @Test
    void eachKindShowsOnlyWhatItMay() {
        assertThat(Sensitive.aadhaar("234567890123").masked()).isEqualTo("XXXX XXXX 0123");
        assertThat(Sensitive.card("4111111111111111").masked()).isEqualTo("XXXX XXXX XXXX 1111");
        assertThat(Sensitive.account("50100012345678").masked()).isEqualTo("XXXXXXXXXX5678");
        assertThat(Sensitive.mobile("9876543210").masked()).isEqualTo("XXXXXX3210");
        assertThat(Sensitive.email("asha.rao@example.com").masked()).isEqualTo("a***@example.com");
    }

    @Test
    void tooShortOrOddValuesShowNothing() {
        assertThat(Sensitive.card("1234567").masked()).isEqualTo("XXXX XXXX XXXX XXXX");
        assertThat(Sensitive.account("123").masked()).isEqualTo("XXXX");
        assertThat(Sensitive.email("@example.com").masked()).isEqualTo("***");
        assertThat(Sensitive.email("no-at-sign").masked()).isEqualTo("***");
    }

    @Test
    void toStringIsMaskedSoLogsAreToo() {
        Customers.Card card = new Customers.Card("VISA", Sensitive.card("4111111111111111"), "08/29");
        assertThat(card.toString()).doesNotContain("4111111111111111").contains("XXXX XXXX XXXX 1111");
        assertThat(List.of(Sensitive.aadhaar("234567890123")).toString()).isEqualTo("[XXXX XXXX 0123]");
    }
}
