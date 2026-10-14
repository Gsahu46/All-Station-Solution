package com.tijori.wallets;

import org.junit.jupiter.api.Test;

import java.util.Currency;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The value object on its own: equality, currency safety, immutability, decimals and overflow. */
class MoneyTest {

    static final Currency INR = Currency.getInstance("INR");
    static final Currency USD = Currency.getInstance("USD");
    static final Currency JPY = Currency.getInstance("JPY");

    @Test
    void equalAmountsAreEqualWhateverTheTrailingZeros() {
        Money a = Money.parse("10.5", INR);
        Money b = Money.parse("10.50", INR);
        assertThat(a).isEqualTo(b).hasSameHashCodeAs(b);
        assertThat(a.minorUnits()).isEqualTo(1050);
        assertThat(Money.parse("10.50", USD)).isNotEqualTo(b);   // same number, different currency
    }

    @Test
    void addingDifferentCurrenciesIsRefused() {
        assertThatThrownBy(() -> Money.parse("100", INR).plus(Money.parse("5", USD)))
                .isInstanceOf(Money.CurrencyMismatchException.class)
                .hasMessage("Cannot combine 100.00 INR with 5.00 USD: different currencies.");
    }

    @Test
    void plusReturnsANewValueAndChangesNeither() {
        Money a = Money.parse("1", INR);
        Money b = Money.parse("2", INR);
        assertThat(a.plus(b)).isEqualTo(Money.parse("3", INR));
        assertThat(a).isEqualTo(Money.parse("1", INR));
        assertThat(b).isEqualTo(Money.parse("2", INR));
    }

    @Test
    void decimalsFollowTheCurrency() {
        assertThat(Money.parse("1500", JPY).toString()).isEqualTo("1500 JPY");
        assertThat(Money.parse("0.1", INR).toString()).isEqualTo("0.10 INR");
        assertThatThrownBy(() -> Money.parse("0.105", INR)).isInstanceOf(ArithmeticException.class);
        assertThatThrownBy(() -> Money.parse("1.5", JPY)).isInstanceOf(ArithmeticException.class);
    }

    @Test
    void overflowIsAnErrorNotAWrapAround() {
        Money huge = new Money(Long.MAX_VALUE, INR);
        assertThatThrownBy(() -> huge.plus(new Money(1, INR))).isInstanceOf(ArithmeticException.class);
    }
}
